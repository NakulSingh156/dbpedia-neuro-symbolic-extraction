#!/usr/bin/env python3
"""
OCCURRENCE — how often do real abstract sentences refer to an entity they never name?

Rebuilds every sentence of the 2,000-abstract Phase 1 run IN ORDER (the run's own
outputs keep sentences but not their order or neighbours), by re-fetching each
abstract from the local store and re-splitting it with the same canonical
splitter the run used. Then draws a uniform, seeded sample for full manual
labelling (stage 1). Stage 2 (scan.py) covers all sentences for the rare class.
"""
import json, os, random, sys, requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from sentence_split import split_sentences  # noqa: E402

S = "http://localhost:7878/query"
N, SEED = 300, 7


def q(x):
    r = requests.post(S, data={"query": x}, headers={"Accept": "application/sparql-results+json"}, timeout=300)
    r.raise_for_status()
    return r.json()["results"]["bindings"]


def main():
    T = [json.loads(l) for l in open(os.path.join(ROOT, "phase1_full", "triples.jsonl"))]
    K = [json.loads(l) for l in open(os.path.join(ROOT, "phase1_full", "skipped.jsonl"))]
    run_sents = {(r["abstract_uri"], r["sentence"]) for r in T + K}
    uris = sorted({u for u, _ in run_sents})
    text = {}
    for i in range(0, len(uris), 200):
        rows = q("SELECT ?s ?o WHERE { VALUES ?s { " + " ".join(f"<{u}>" for u in uris[i:i + 200])
                 + " } ?s <http://www.w3.org/2000/01/rdf-schema#comment> ?o }")
        for b in rows:
            text.setdefault(b["s"]["value"], b["o"]["value"])
    allsents, matched = [], 0
    for u in uris:
        if u not in text:
            continue
        sents = split_sentences(text[u])
        for k, s in enumerate(sents):
            matched += (u, s) in run_sents
            allsents.append({"id": f"{len(allsents):05d}", "abstract_uri": u,
                             "topic": u.rsplit("/", 1)[-1].replace("_", " "),
                             "pos": k, "n_in_abstract": len(sents),
                             "prev": sents[k - 1] if k else "", "sentence": s})
    with open(os.path.join(HERE, "all_sentences.jsonl"), "w") as fh:
        for x in allsents:
            fh.write(json.dumps(x, ensure_ascii=False) + "\n")
    smp = sorted(random.Random(SEED).sample(allsents, N), key=lambda x: x["id"])
    with open(os.path.join(HERE, f"sample_{N}.jsonl"), "w") as fh:
        for x in smp:
            fh.write(json.dumps(x, ensure_ascii=False) + "\n")
    print(f"abstracts fetched {len(text)}/{len(uris)} | sentences rebuilt {len(allsents)} "
          f"(run had {len(run_sents)}; {matched} match exactly) | sample {N}, seed {SEED}")


if __name__ == "__main__":
    main()
