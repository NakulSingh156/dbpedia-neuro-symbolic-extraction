#!/usr/bin/env python3
"""
PHASE 1 — extract RDF from real Wikipedia abstracts and produce an audit sample.

This is the product track, not the benchmark track. It answers the one question
no benchmark can: what is the precision of this pipeline on OPEN-DOMAIN text,
where there is no per-domain list of allowed predicates to constrain it?

Differences from the benchmark runner
-------------------------------------
* Input is abstracts sampled from the local store, not benchmark test sentences.
* No gold, so nothing is scored — the output is audited by humans instead.
* No `allowed_predicates`: the pipeline ranks over the FULL DBpedia ontology,
  which is the production setting and the source of the predicate drift seen in
  Phase 0 (e.g. `programCost "baccalaureate programs"`).
* Every emitted triple is tagged `verified` or `faithful-unverified` by asking
  the store whether it already exists. The unverified slice is the new knowledge
  — that slice is the product.

Provenance is preserved per triple (source abstract URI + source sentence), so
an auditor can judge each triple against the exact text it came from.

Usage
-----
    python scripts/run_phase1_abstracts.py --n 2000 --model qwen2.5:7b
    python scripts/run_phase1_abstracts.py --n 100 --model qwen2.5:7b --tag pilot

Outputs (in phase1_<tag>/):
    triples.jsonl      every triple with provenance and verification status
    audit_sample.tsv   200 random triples, ready for manual review
    stats.json         yield, verified fraction, timings
"""
import argparse, json, os, random, re, sys, time
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=2000, help="number of abstracts")
ap.add_argument("--model", default="qwen2.5:7b")
ap.add_argument("--ollama", default="http://localhost:11434/v1")
ap.add_argument("--sparql", default="http://localhost:7878/query")
ap.add_argument("--tag", default="qwen7b")
ap.add_argument("--audit-size", type=int, default=200)
ap.add_argument("--seed", type=int, default=42)
ap.add_argument("--sentence-timeout", type=int, default=1800)
args = ap.parse_args()

OUT = os.path.join(ROOT, f"phase1_{args.tag}")
os.makedirs(OUT, exist_ok=True)

os.environ["USE_TF"] = "0"
os.environ.setdefault("OPENROUTER_API_KEY", "ollama")
sys.path.insert(0, SRC)
import autonomous_pipeline_v13 as pl                      # noqa: E402

pl.OPENROUTER_BASE_URL = args.ollama
pl.OPENROUTER_API_KEY = "ollama"
pl.TARGET_MODEL = args.model
pl.USE_LOCAL_INDEX = True
pl.DBPEDIA_SPARQL_ENDPOINT = args.sparql
# Product track: never emit a URI that is not a real DBpedia entity. The Phase-1
# pilot measured 31.6% of triples referencing invented URIs on open-domain text.
pl.STRICT_URI_MODE = True

ABBR = (r"(?:Dr|Mr|Mrs|Ms|St|Jr|Sr|Prof|Rev|Gen|Col|Capt|Lt|Sgt|Inc|Ltd|Co|Corp"
        r"|No|vs|etc|e\.g|i\.e|Mt|Ft|Ave|approx|Fig|Vol|pp)")


def split_sentences(t):
    """Abbreviation-aware split; same rule used for the workload counts in the
    scaling proposal, so sentence counts stay consistent between the two."""
    s = re.sub(rf"\b{ABBR}\.", lambda m: m.group(0).replace(".", "<D>"), t)
    s = re.sub(r"\b([A-Z])\.", r"\1<D>", s)
    s = re.sub(r"(\d)\.(\d)", r"\1<D>\2", s)
    parts = re.split(r"(?<=[.!?])[\"')\]]*\s+(?=[A-Z\"'(\[])", s)
    return [p.replace("<D>", ".").strip() for p in parts
            if len(p.replace("<D>", ".").strip()) > 15]


def sparql(q):
    r = requests.get(args.sparql, params={"query": q, "format": "json"}, timeout=60)
    r.raise_for_status()
    return r.json()


def sample_abstracts(n, seed):
    """Stratified sample across the corpus, mirroring sample_abstract_stats.py so
    Phase 1's inputs are drawn the same way the workload estimate was."""
    total = 4643098
    strata, per = 20, max(1, n // 20)
    rnd = random.Random(seed)
    out = []
    for i in range(strata):
        off = (i * (total // strata)) + rnd.randint(0, 1000)
        q = ("SELECT ?s ?o WHERE { ?s <http://www.w3.org/2000/01/rdf-schema#comment> ?o } "
             f"OFFSET {off} LIMIT {per * 2}")
        for b in sparql(q)["results"]["bindings"]:
            if len(b["o"]["value"]) > 40:
                out.append((b["s"]["value"], b["o"]["value"]))
            if len(out) >= (i + 1) * per:
                break
    return out[:n]


def verify(sub, rel, obj):
    """Post-hoc: does DBpedia already contain this triple?

    Derived by asking the store rather than by instrumenting the pipeline, so
    the frozen v14-final code stays byte-identical to the benchmark runs."""
    if obj.startswith('"'):
        return "literal"                      # literal objects are not URI-verifiable
    R = "http://dbpedia.org/resource/"
    O = "http://dbpedia.org/ontology/"
    q = f'ASK {{ <{R}{sub}> <{O}{rel}> <{R}{obj}> }}'
    try:
        return "verified" if sparql(q).get("boolean") else "faithful-unverified"
    except Exception:
        return "unchecked"


def main():
    for name, url in (("Ollama", args.ollama.replace("/v1", "") + "/api/tags"),
                      ("SPARQL", None)):
        try:
            if url:
                requests.get(url, timeout=5).raise_for_status()
            else:
                sparql("ASK { ?s ?p ?o }")
            print(f"🟢 {name} reachable")
        except Exception as e:
            sys.exit(f"🔴 {name} unreachable: {e}")
    if not pl.REDIS_AVAILABLE:
        sys.exit("🔴 Redis surface-form index not connected")
    print(f"🟢 Redis index ({pl.redis_client.dbsize():,} keys)")

    ns = {"extract_all_triples": pl.extract_all_triples}
    exec(open(os.path.join(SRC, "per_sentence_timeout.py")).read(), ns)
    ns["_HARD_LIMIT"] = args.sentence_timeout
    extract = ns["extract_all_triples"]

    print(f"\nsampling {args.n} abstracts...")
    abstracts = sample_abstracts(args.n, args.seed)
    print(f"got {len(abstracts)} abstracts\n")

    dest = os.path.join(OUT, "triples.jsonl")
    done = set()
    if os.path.exists(dest):                       # resume
        for line in open(dest):
            done.add(json.loads(line)["abstract_uri"])
        print(f"resuming — {len(done)} abstracts already processed")

    t0, n_sent, n_trip = time.time(), 0, 0
    with open(dest, "a") as fh:
        for i, (uri, text) in enumerate(abstracts, 1):
            if uri in done:
                continue
            for sent in split_sentences(text):
                n_sent += 1
                try:
                    out = extract(sent, verbose=False)   # NO allowed_predicates
                except Exception as e:
                    print(f"  sentence errored: {str(e)[:80]}")
                    continue
                for t in out.get("triples", []):
                    rec = {"abstract_uri": uri, "sentence": sent,
                           "sub": t["sub"], "rel": t["rel"], "obj": t["obj"],
                           "status": verify(t["sub"], t["rel"], t["obj"])}
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    n_trip += 1
                fh.flush()
            el = (time.time() - t0) / 3600
            rate = i / el if el else 0
            print(f"[{i}/{len(abstracts)}] {n_trip} triples | {n_sent} sentences | "
                  f"{el:.1f}h | eta {(len(abstracts)-i)/rate if rate else 0:.1f}h", flush=True)

    rows = [json.loads(l) for l in open(dest)]
    rnd = random.Random(args.seed)
    audit = rnd.sample(rows, min(args.audit_size, len(rows)))
    with open(os.path.join(OUT, "audit_sample.tsv"), "w") as fh:
        fh.write("correct?\tsub\trel\tobj\tstatus\tsentence\n")
        for r in audit:
            fh.write(f"\t{r['sub']}\t{r['rel']}\t{r['obj']}\t{r['status']}\t{r['sentence']}\n")

    from collections import Counter
    c = Counter(r["status"] for r in rows)
    stats = {"abstracts": len(abstracts), "sentences": n_sent, "triples": len(rows),
             "triples_per_sentence": round(len(rows) / max(n_sent, 1), 2),
             "status_counts": dict(c), "hours": round((time.time() - t0) / 3600, 2),
             "model": args.model}
    json.dump(stats, open(os.path.join(OUT, "stats.json"), "w"), indent=1)
    print("\n" + json.dumps(stats, indent=1))
    print(f"\naudit sample -> {OUT}/audit_sample.tsv  (fill the 'correct?' column)")


if __name__ == "__main__":
    main()
