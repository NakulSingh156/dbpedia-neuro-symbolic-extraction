#!/usr/bin/env python3
"""
NO-METHOD BASELINE — plain few-shot prompting on Text2KGBench dbpedia_webnlg.

Isolates the base-model contribution. No surface-form index, no SPARQL gate,
no judge, no math funnel, no learned formatting conventions. One LLM call per
sentence, then the official scorer.

Uses the benchmark's OWN prompt header (ontology concepts + relations, taken
verbatim from data/dbpedia_webnlg/baselines/prompts/) and its `rel(sub, obj)`
output format, so the run is faithful to the published baselines. The only
addition is N in-context examples drawn deterministically from the train split.

Run it once per model to get a controlled model comparison:

    python scripts/baseline_fewshot.py --model openai/gpt-5.6-luna --tag luna
    python scripts/baseline_fewshot.py --model openai/gpt-4o        --tag gpt4o

Results land in baseline_<tag>/results_<domain>.json and are resumable —
re-running skips domains already on disk.
"""
import argparse, json, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from text2kg_harness import (BENCH, load_test, load_train, load_ground_truth,
                             score_sentence, all_domains, _require_bench)
from openai import OpenAI

SHOTS = 6
CONCURRENCY = 8


def prompt_header(slug):
    """Instructions + ontology block from the official prompt file, verbatim."""
    path = f"{BENCH}/baselines/prompts/ont_{slug}_prompts.jsonl"
    with open(path) as f:
        first = json.loads(f.readline())
    # everything before the worked example is the reusable header
    return first["prompt"].split("Example Sentence:")[0].rstrip()


def fmt_triples(triples):
    return "\n".join(f'{t["rel"]}({t["sub"]}, {t["obj"]})' for t in triples)


def build_prompt(header, shots, sentence):
    blocks = [header, ""]
    for ex in shots:
        blocks.append(f"Example Sentence: {ex['sent']}")
        blocks.append("Example Output:")
        blocks.append(fmt_triples(ex["triples"]))
        blocks.append("")
    blocks.append(f"Test Sentence: {sentence}")
    blocks.append("Test Output: ")
    return "\n".join(blocks)


def parse_output(text):
    """Parse `rel(sub, obj)` lines. Handles nested parens in entity names,
    e.g. creator(Asterix (comicsCharacter), René Goscinny)."""
    out = []
    for line in text.strip().splitlines():
        line = line.strip().rstrip(".").strip()
        if not line or line.lower().startswith(("test output", "example")):
            continue
        m = re.match(r"^([A-Za-z_][\w/]*)\s*\((.*)\)\s*$", line)
        if not m:
            continue
        rel, inner = m.group(1), m.group(2)
        depth = 0
        for i, ch in enumerate(inner):          # split on the TOP-LEVEL comma
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "," and depth == 0:
                out.append({"sub": inner[:i].strip(),
                            "rel": rel,
                            "obj": inner[i + 1:].strip()})
                break
    return out


def run_domain(client, model, slug, outdir):
    dest = f"{outdir}/results_{slug}.json"
    if os.path.exists(dest):                     # resume
        rows = json.load(open(dest))
        return sum(r["f1"] for r in rows) / len(rows), len(rows), True

    header = prompt_header(slug)
    shots = load_train(slug)[:SHOTS]             # deterministic, reproducible
    tests = load_test(slug)
    gold = load_ground_truth(slug)

    def one(t):
        prompt = build_prompt(header, shots, t["sent"])
        pred, err = [], None
        for attempt in range(3):
            try:
                r = client.chat.completions.create(
                    model=model, temperature=0,
                    messages=[{"role": "user", "content": prompt}],
                )
                pred = parse_output(r.choices[0].message.content or "")
                err = None
                break
            except Exception as e:
                err = str(e)[:200]
                time.sleep(2 * (attempt + 1))
        p, rc, f1 = score_sentence(pred, gold.get(t["id"], []))
        return {"id": t["id"], "sent": t["sent"], "pred": pred,
                "gold": gold.get(t["id"], []), "p": p, "r": rc, "f1": f1,
                "error": err}

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        rows = list(pool.map(one, tests))

    os.makedirs(outdir, exist_ok=True)
    json.dump(rows, open(dest, "w"), indent=1)
    return sum(r["f1"] for r in rows) / len(rows), len(rows), False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--domains", nargs="*", default=None)
    args = ap.parse_args()

    _require_bench()
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("set OPENROUTER_API_KEY")
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)

    outdir = f"baseline_{args.tag}"
    os.makedirs(outdir, exist_ok=True)
    slugs = args.domains or all_domains()

    print(f"model={args.model}  shots={SHOTS}  domains={len(slugs)}\n")
    scores = []
    t0 = time.time()
    for slug in slugs:
        f1, n, cached = run_domain(client, args.model, slug, outdir)
        scores.append(f1)
        mark = "(cached)" if cached else ""
        print(f"{slug:26s} F1={f1:.4f}  n={n:4d}  "
              f"[{(time.time()-t0)/60:.0f} min] {mark}")

    print(f"\n=== {args.tag.upper()} {SHOTS}-SHOT BASELINE, NO METHOD ===")
    print(f"=== MACRO F1 over {len(scores)} domains: {sum(scores)/len(scores):.4f} ===")


if __name__ == "__main__":
    main()
