#!/usr/bin/env python3
"""
COVERAGE — does DBpedia have the relation at all?

The uniqueness survey measures how often `X <p> ?x` has one answer GIVEN that X
has some value for p. Grounding also needs that value to exist. Real grounding
rate = coverage x uniqueness, and on Phase 1 data coverage is the bottleneck.

Proxy population: Phase 1 relational triples (entity object, relation present in
the store). For each, does the extracted SUBJECT have any value for that
relation? Caveat — this understates true coverage for well-formed descriptions:
a low number mixes real KB gaps with (a) the pipeline choosing a different
property than DBpedia uses for that type (nationality vs citizenship) and (b)
mislinked subjects, at ~60% open-domain precision.
"""
import collections, json, os, requests
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
S = "http://localhost:7878/query"; R = "http://dbpedia.org/resource/"; O = "http://dbpedia.org/ontology/"

def q(x):
    r = requests.post(S, data={"query": x}, headers={"Accept": "application/sparql-results+json"}, timeout=300)
    r.raise_for_status(); return r.json()["results"]["bindings"]

sv = json.load(open(os.path.join(HERE, "results", "uniqueness_survey.json")))["results"]
F = [json.loads(l) for l in open(os.path.join(ROOT, "phase1_full", "triples.jsonl"))]
uri = [r for r in F if r["status"] in ("verified", "faithful-unverified")
       and sv.get(r["rel"], {}).get("fwd", {}).get("anchors", 0) > 0]
pairs = collections.defaultdict(set)
for r in uri: pairs[r["rel"]].add(r["sub"])
covered = set()
for rel, subs in pairs.items():
    subs = sorted(subs)
    for i in range(0, len(subs), 300):
        rows = q("SELECT DISTINCT ?s WHERE { VALUES ?s { " + " ".join(f"<{R}{s}>" for s in subs[i:i + 300])
                 + f" }} ?s <{O}{rel}> ?v . FILTER(isIRI(?v)) }}")
        covered |= {(rel, b["s"]["value"][len(R):]) for b in rows}

def uniq(rel):
    f = sv[rel]["fwd"]; return f.get("pct_unique_containment", f["pct_exactly_1"]) / 100

cov = [(r["rel"], r["sub"]) in covered for r in uri]
by = collections.defaultdict(lambda: [0, 0])
for r, ok in zip(uri, cov): by[r["rel"]][0] += ok; by[r["rel"]][1] += 1
out = {"n_triples": len(uri),
       "coverage_pct": round(100 * sum(cov) / len(uri), 1),
       "expected_grounding_pct": round(100 * sum(uniq(r["rel"]) for r, ok in zip(uri, cov) if ok) / len(uri), 1),
       "by_relation": {k: {"covered": a, "n": n, "pct": round(100 * a / n, 1)} for k, (a, n) in by.items()}}
json.dump(out, open(os.path.join(HERE, "results", "coverage.json"), "w"), indent=1)
print(f"coverage {out['coverage_pct']}%  expected grounding {out['expected_grounding_pct']}%  (n={len(uri)})")
