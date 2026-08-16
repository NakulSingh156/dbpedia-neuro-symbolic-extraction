#!/usr/bin/env python3
"""
LOCAL OPEN-MODEL BENCHMARK — run the full NEF 2.0 pipeline against a model
served locally by Ollama, with zero API cost.

Answers: does an open-weight model hold up on the v14 pipeline? Our only
open-model datapoint (LLaMA-3.3-70B, 0.4387) predates the local index, the
SPARQL gate and every v14 fix, so it says nothing about the current system.

What changes vs. the paid run — ONLY the LLM endpoint. The surface-form index,
the SPARQL gate, Node 3, the judge and all learned formatting are identical, so
the delta is attributable to the model alone.

Prerequisites
-------------
  1. ollama serve                       (daemon running)
  2. ollama pull qwen2.5:7b             (or any model you want to test)
  3. Redis surface-form index on 6380   (already on this machine)
  4. SPARQL store reachable. It lives on the server, so open a tunnel first:
         ssh -N -L 7878:localhost:7878 root@<server>
     ...and leave that terminal open for the whole run.

Usage
-----
    python scripts/run_local_model.py --model qwen2.5:7b --tag qwen7b

Long runs: prefix with nohup so it survives terminal close and SSH drop (NOT sleep — see below):

    nohup python scripts/run_local_model.py --model qwen2.5:7b --tag qwen7b \
         > local_qwen7b.log 2>&1 &
    tail -f local_qwen7b.log

macOS sleep will PAUSE the run. Keep the lid open on power, and wrap in
caffeinate to block idle sleep:

    caffeinate -i nohup python scripts/run_local_model.py ... &

Resumable: each domain is written to <outdir>/results_<slug>.json as it finishes,
and an existing file is skipped, so re-running continues where it stopped.
"""
import argparse, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="qwen2.5:7b", help="Ollama model tag")
ap.add_argument("--tag", default=None, help="output dir suffix (default: model name)")
ap.add_argument("--ollama", default="http://localhost:11434/v1")
ap.add_argument("--sparql", default="http://localhost:7878/query")
ap.add_argument("--sentence-timeout", type=int, default=1800,
                help="hard wall per sentence; local inference is far slower than an API")
ap.add_argument("--call-timeout", type=int, default=600,
                help="cap on a single LLM call")
ap.add_argument("--chunk-size", type=int, default=22)
ap.add_argument("--domains", nargs="*", default=None)
args = ap.parse_args()

tag = args.tag or args.model.replace(":", "").replace("/", "_")
OUTDIR = os.path.join(ROOT, f"local_{tag}")

# ── env must be set BEFORE importing the pipeline ────────────────────────────
os.environ["USE_TF"] = "0"
os.environ.setdefault("OPENROUTER_API_KEY", "ollama")   # Ollama ignores the value

sys.path.insert(0, SRC)
import autonomous_pipeline_v13 as pl                     # noqa: E402
# NOTE: per_sentence_timeout.py is not importable — it reads `extract_all_triples`
# from the namespace it is exec'd into and rebinds it to the wrapped version.
# It is exec'd in main(), after that namespace exists.

# ── point every knob at local infrastructure ─────────────────────────────────
# _make_llm() reads these module globals on every call, so runtime override works.
pl.OPENROUTER_BASE_URL = args.ollama
pl.OPENROUTER_API_KEY = "ollama"
pl.TARGET_MODEL = args.model
pl.USE_LOCAL_INDEX = True
pl.DBPEDIA_SPARQL_ENDPOINT = args.sparql
pl.LLM_TIMEOUT_SECONDS = args.call_timeout

# (the per-sentence wall is raised in main(), once the breaker is loaded)


def preflight():
    """Fail loudly now rather than 40 minutes into a run."""
    import requests
    ok = True
    try:
        tags = requests.get(args.ollama.replace("/v1", "") + "/api/tags", timeout=5).json()
        names = [m["name"] for m in tags.get("models", [])]
        if not names:
            print("🔴 Ollama has no models. Run:  ollama pull " + args.model); ok = False
        elif not any(n == args.model or n.startswith(args.model.split(":")[0]) for n in names):
            print(f"🔴 model '{args.model}' not pulled. Available: {names}"); ok = False
        else:
            print(f"🟢 Ollama serving: {names}")
    except Exception as e:
        print(f"🔴 Ollama not reachable at {args.ollama} ({e}). Run: ollama serve"); ok = False

    try:
        r = requests.get(args.sparql, params={"query": "ASK { ?s ?p ?o }", "format": "json"},
                         timeout=8)
        print("🟢 SPARQL store reachable" if r.status_code == 200
              else f"🔴 SPARQL returned {r.status_code}")
        ok = ok and r.status_code == 200
    except Exception as e:
        print(f"🔴 SPARQL not reachable at {args.sparql} ({e}).")
        print("   Open the tunnel:  ssh -N -L 7878:localhost:7878 root@<server>")
        ok = False

    if not pl.REDIS_AVAILABLE:
        print("🔴 Redis surface-form index not connected on 6380."); ok = False
    else:
        print(f"🟢 Redis index connected ({pl.redis_client.dbsize():,} keys)")
    return ok


def main():
    if not preflight():
        sys.exit("\npreflight failed — fix the above and re-run.")

    ns = {"extract_all_triples": pl.extract_all_triples}

    # Circuit breaker: wraps extract_all_triples so one hung sentence can't
    # freeze the run. Must be exec'd AFTER extract_all_triples exists, and the
    # wall raised AFTER exec (the wrapper reads _HARD_LIMIT from ns at call
    # time, and the module hardcodes 180s — far too low for local inference).
    exec(open(os.path.join(SRC, "per_sentence_timeout.py")).read(), ns)
    ns["_HARD_LIMIT"] = args.sentence_timeout
    print(f"   per-sentence wall raised to {args.sentence_timeout}s for local inference")

    exec(open(os.path.join(SRC, "chunked_runner.py")).read(), ns)

    slugs = args.domains or ns["all_domains"]() if "all_domains" in ns else args.domains
    if not slugs:
        from text2kg_harness import all_domains
        slugs = all_domains()

    os.makedirs(OUTDIR, exist_ok=True)
    os.chdir(OUTDIR)          # chunked_domain writes results_<slug>.json to CWD

    print(f"\nmodel={args.model}  sentence-wall={args.sentence_timeout}s  "
          f"domains={len(slugs)}  out={OUTDIR}\n")

    t0, scores = time.time(), []
    for slug in slugs:
        dest = f"results_{slug}.json"
        if os.path.exists(dest):
            rows = json.load(open(dest))
            f1 = sum(r["f1"] for r in rows) / len(rows)
            scores.append(f1)
            print(f"{slug:26s} F1={f1:.4f}  n={len(rows):4d}  (cached)", flush=True)
            continue

        # chunk_cooldown exists to reset an API rate-limit window; irrelevant locally.
        P, R, F, rows = ns["chunked_domain"](slug, chunk_size=args.chunk_size,
                                             chunk_cooldown=0)
        scores.append(F)
        print(f"\n>>> {slug:24s} F1={F:.4f}  n={len(rows):4d}  "
              f"[{(time.time()-t0)/3600:.1f} h elapsed]\n", flush=True)

    if scores:
        print(f"\n=== {args.model} — FULL PIPELINE, LOCAL ===")
        print(f"=== MACRO F1 over {len(scores)} domains: {sum(scores)/len(scores):.4f} ===")


if __name__ == "__main__":
    main()
