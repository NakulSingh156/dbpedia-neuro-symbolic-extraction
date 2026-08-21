#!/usr/bin/env python3
"""
CORPUS WORKLOAD ESTIMATE — how much text does a full extraction run have to chew?

Feeds the sentence and abstract counts in SCALING_PROPOSAL.md. Two corrections
over the version that produced the original estimate:

  1. Reads the LOCAL oxigraph store. The original SSH'd to the server, which no
     longer needs to exist for this to run.
  2. Uses the canonical splitter (scripts/sentence_split.py). The original
     counted with a rule that required whitespace after a full stop, so every
     glued boundary ("...1969.He was born...") counted as ONE sentence instead
     of two — biasing the workload estimate DOWN by roughly 9%.

Artifact criteria are applied and reported separately rather than folded into a
single percentage, so a reviewer can disagree with any one of them.

Usage
-----
    python scripts/sample_abstract_stats.py --n 5000
"""
import argparse, json, math, os, re, statistics as st, sys
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sentence_split import split_sentences               # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=5000)
ap.add_argument("--sparql", default="http://localhost:7878/query")
ap.add_argument("--strata", type=int, default=20)
ap.add_argument("--total", type=int, default=4643098, help="corpus size (abstracts)")
ap.add_argument("--out", default="abstract_stats.json")
args = ap.parse_args()

DISAMBIG = re.compile(r"\bmay (also )?refer to\b", re.I)
LISTPAGE = re.compile(r"^\s*(This is a |)list of\b", re.I)


def sparql(q):
    r = requests.get(args.sparql, params={"query": q, "format": "json"}, timeout=300)
    r.raise_for_status()
    return r.json()


def main():
    per, step = max(1, args.n // args.strata), args.total // args.strata
    texts = []
    for i in range(args.strata):
        q = ("SELECT ?o WHERE { ?s <http://www.w3.org/2000/01/rdf-schema#comment> ?o } "
             f"OFFSET {i * step} LIMIT {per}")
        try:
            texts += [b["o"]["value"] for b in sparql(q)["results"]["bindings"]]
        except Exception as e:
            print(f"stratum {i} failed: {str(e)[:90]}", flush=True)
        print(f"  stratum {i+1}/{args.strata}  cumulative={len(texts)}", flush=True)

    # ── artifacts, counted by cause ──────────────────────────────────────────
    cause = {"too_short": 0, "disambiguation": 0, "list_page": 0}
    usable = []
    for t in texts:
        if len(t.strip()) < 40:
            cause["too_short"] += 1
        elif DISAMBIG.search(t[:200]):
            cause["disambiguation"] += 1
        elif LISTPAGE.match(t):
            cause["list_page"] += 1
        else:
            usable.append(t)

    n_art = sum(cause.values())
    counts = [len(split_sentences(t)) for t in usable]
    mean = st.mean(counts)
    ci = 1.96 * st.stdev(counts) / math.sqrt(len(counts))
    frac_usable = len(usable) / len(texts)
    est_abs = args.total * frac_usable

    stats = {
        "sampled": len(texts),
        "artifacts": {"total": n_art, "pct": round(100 * n_art / len(texts), 2),
                      "by_cause": cause},
        "usable_abstracts_sampled": len(usable),
        "usable_fraction": round(frac_usable, 4),
        "sentences_per_abstract": {"mean": round(mean, 3),
                                   "ci95": round(ci, 3),
                                   "median": st.median(counts),
                                   "max": max(counts)},
        "corpus_total_abstracts": args.total,
        "projected_usable_abstracts": int(est_abs),
        "projected_sentences": int(est_abs * mean),
        "projected_sentences_ci95": int(est_abs * ci),
        "splitter": "canonical (glued-boundary repair enabled)",
    }
    json.dump(stats, open(args.out, "w"), indent=1)
    print("\n" + json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
