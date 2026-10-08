#!/usr/bin/env python3
"""
UNIQUENESS SURVEY — can a description of an unnamed entity be grounded?

The anonymous-node plan (GSoC26 README, Future work) represents an unnamed
entity as a blank node with constraints — a query — and grounds it against the
store only when the answer is unique:

    "Marie Antoinette's husband"  ->  ?x : spouse(Marie_Antoinette, ?x)  ->  Louis_XVI

That only yields a contribution if real relations resolve uniquely often enough.
If `X <p> ?x` usually returns zero or five answers, the mechanism rarely fires.
This measures, per relation and per direction, how often it returns exactly one.

Two readings of "unique", because the first probe showed they differ a lot:

  STRICT       exactly one value.
  CONTAINMENT  exactly one value after removing values that merely CONTAIN
               another value (Honolulu / Hawaii / United_States for birthPlace
               collapse to Honolulu). Forward direction only — the inverse
               (all people born in Honolulu) has no containment structure.

Population: relations the pipeline actually extracted with an entity object in
the 2,000-abstract Phase 1 run (frequency >= MIN_FREQ, ~92% of that volume),
plus the kinship relations the README's own example uses. Aggregates are
weighted by Phase 1 frequency, so they answer "what fraction of the relational
facts we extract involve a groundable relation".

Sampling: the distinct anchors of each relation are pulled into Python (capped
at --cap; relations hitting the cap are flagged) and --n are drawn UNIFORMLY
with a fixed seed. An earlier version took the first N anchors in the store's
index order; index order clusters similar entities, and a different 300-anchor
slice moved per-relation results by a median 6.6 and up to 45 points (director
75.7% vs 30.7%). That run is kept in results_v1_index_order_BIASED/ as evidence.
--stability re-draws the top relations with a second seed; differences should
sit within binomial noise (about +-5 points at n=400).

Read-only. Needs only the local oxigraph store on :7878.
"""
import argparse, collections, json, os, statistics, sys, time
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DBO = "http://dbpedia.org/ontology/"

ap = argparse.ArgumentParser()
ap.add_argument("--sparql", default="http://localhost:7878/query")
ap.add_argument("--n", type=int, default=400, help="anchors sampled per relation/direction")
ap.add_argument("--cap", type=int, default=300000, help="max distinct anchors pulled per relation")
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--min-freq", type=int, default=3)
ap.add_argument("--multi-cap", type=int, default=80,
                help="multi-answer anchors checked for containment, per relation")
ap.add_argument("--stability", type=int, default=20,
                help="re-draw the top-K relations with a second seed to test sample sensitivity")
ap.add_argument("--phase1", default=os.path.join(ROOT, "phase1_full", "triples.jsonl"))
ap.add_argument("--out", default=os.path.join(HERE, "results"))
args = ap.parse_args()

# The README's own example class: an entity described by its relation to a
# named one. Included even if Phase 1 rarely emitted them.
KINSHIP = ["spouse", "child", "parent", "relative", "relation", "partner"]

# Geographic/organisational containment. One hop is usually enough because
# DBpedia states country/state directly on most places.
CONTAINMENT = ["isPartOf", "country", "state", "region", "locatedInArea",
               "department", "county", "province", "district", "federalState",
               "subdivision", "parentOrganisation"]


def q(query, timeout=180, tries=3):
    for i in range(tries):
        try:
            # POST, not GET: VALUES lists of a few hundred IRIs exceed the URL
            # length the server accepts (HTTP 400), which silently failed the
            # containment check on 73 of 151 relations in the first run.
            r = requests.post(args.sparql, data={"query": query},
                              headers={"Accept": "application/sparql-results+json"},
                              timeout=timeout)
            if r.status_code == 200:
                return r.json()["results"]["bindings"]
        except Exception:
            pass
        time.sleep(2 * (i + 1))
    return None          # distinguish "query failed" from "no rows"


import random
_pools = {}


def anchor_pool(prop, direction):
    """Distinct anchors for a relation, capped. Cached per (prop, direction)."""
    key = (prop, direction)
    if key not in _pools:
        P = DBO + prop
        inner = (f"?a <{P}> ?x . FILTER(isIRI(?x))" if direction == "fwd"
                 else f"?x <{P}> ?a . FILTER(isIRI(?a))")
        rows = q(f"SELECT DISTINCT ?a WHERE {{ {inner} }} LIMIT {args.cap}", timeout=600)
        _pools[key] = None if rows is None else [b["a"]["value"] for b in rows]
    return _pools[key]


def counts(prop, direction, seed=None):
    pool = anchor_pool(prop, direction)
    if pool is None:
        return None, False
    if not pool:
        return {}, False
    smp = random.Random(args.seed if seed is None else seed).sample(pool, min(args.n, len(pool)))
    P = DBO + prop
    pat = (f"?a <{P}> ?v . FILTER(isIRI(?v))" if direction == "fwd" else f"?v <{P}> ?a")
    rows = q("SELECT ?a (COUNT(DISTINCT ?v) AS ?n) WHERE { VALUES ?a { "
             + " ".join(f"<{a}>" for a in smp) + f" }} {pat} }} GROUP BY ?a")
    if rows is None:
        return None, False
    return {b["a"]["value"]: int(b["n"]["value"]) for b in rows}, len(pool) >= args.cap


def containment_unique(prop, multi_anchors):
    """For anchors with >1 forward value: does exactly one value survive once
    values that contain another value are removed?"""
    if not multi_anchors:
        return 0, 0
    P = DBO + prop
    vals_rows = q("SELECT ?a ?v WHERE { VALUES ?a { "
                  + " ".join(f"<{a}>" for a in multi_anchors)
                  + f" }} ?a <{P}> ?v . FILTER(isIRI(?v)) }}")
    if vals_rows is None:
        return None, None
    by_anchor = collections.defaultdict(set)
    for b in vals_rows:
        by_anchor[b["a"]["value"]].add(b["v"]["value"])
    all_vals = set().union(*by_anchor.values()) if by_anchor else set()
    if not all_vals:
        return 0, 0
    cps = " ".join(f"<{DBO}{c}>" for c in CONTAINMENT)
    edges = set()                         # (child, container)
    vlist = sorted(all_vals)
    for i in range(0, len(vlist), 200):
        rows = q("SELECT ?u ?w WHERE { VALUES ?u { "
                 + " ".join(f"<{v}>" for v in vlist[i:i + 200])
                 + f" }} VALUES ?cp {{ {cps} }} ?u ?cp ?w . FILTER(isIRI(?w)) }}")
        if rows is None:
            return None, None
        for b in rows:
            if b["w"]["value"] in all_vals:
                edges.add((b["u"]["value"], b["w"]["value"]))
    collapsed = 0
    for a, vs in by_anchor.items():
        containers = {w for (u, w) in edges if u in vs and w in vs and u != w}
        if len(vs - containers) == 1:
            collapsed += 1
    return collapsed, len(by_anchor)


def summarise(cs):
    ns = list(cs.values())
    if not ns:
        return {"anchors": 0}
    return {"anchors": len(ns),
            "pct_exactly_1": round(100 * sum(1 for n in ns if n == 1) / len(ns), 1),
            "pct_2_to_5": round(100 * sum(1 for n in ns if 2 <= n <= 5) / len(ns), 1),
            "pct_over_5": round(100 * sum(1 for n in ns if n > 5) / len(ns), 1),
            "median": statistics.median(ns), "max": max(ns)}


def main():
    try:
        ok = requests.get(args.sparql, params={"query": "ASK { ?s ?p ?o }", "format": "json"},
                          timeout=30).json().get("boolean")
    except Exception as e:
        ok = False
    if not ok:
        sys.exit(f"store unreachable at {args.sparql}")
    rows = [json.loads(l) for l in open(args.phase1)]
    freq = collections.Counter(r["rel"] for r in rows
                               if r["status"] in ("verified", "faithful-unverified"))
    population = [p for p, n in freq.most_common() if n >= args.min_freq]
    for k in KINSHIP:
        if k not in population:
            population.append(k)
    print(f"surveying {len(population)} relations  (n={args.n} anchors/direction)\n", flush=True)

    os.makedirs(args.out, exist_ok=True)
    results, t0 = {}, time.time()
    for i, p in enumerate(population, 1):
        (fwd, fcap), (inv, icap) = counts(p, "fwd"), counts(p, "inv")
        rec = {"relation": p, "phase1_freq": freq.get(p, 0),
               "fwd": summarise(fwd or {}), "inv": summarise(inv or {}),
               "fwd_pool_capped": fcap, "inv_pool_capped": icap,
               "query_failed": fwd is None or inv is None,
               "containment_failed": False}
        if fwd:
            multi = [a for a, n in fwd.items() if n > 1][:args.multi_cap]
            col, checked = containment_unique(p, multi)
            if col is None:
                rec["containment_failed"] = True
            if col is not None and rec["fwd"]["anchors"]:
                strict1 = sum(1 for n in fwd.values() if n == 1)
                # extrapolate the checked share of multi-answer anchors to all of them
                n_multi = sum(1 for n in fwd.values() if n > 1)
                rescued = (col / checked * n_multi) if checked else 0
                rec["fwd"]["pct_unique_containment"] = round(
                    100 * (strict1 + rescued) / rec["fwd"]["anchors"], 1)
                rec["fwd"]["containment_checked"] = checked
        results[p] = rec
        f, v = rec["fwd"], rec["inv"]
        print(f"[{i:3d}/{len(population)}] {p:26s} freq={rec['phase1_freq']:4d}  "
              f"fwd 1={f.get('pct_exactly_1','-'):>5}% cont={f.get('pct_unique_containment','-'):>5}%  "
              f"inv 1={v.get('pct_exactly_1','-'):>5}%   [{time.time()-t0:.0f}s]", flush=True)

    # sample-sensitivity: same relations, a different slice
    stab = {}
    for p in [p for p in population if results[p]["fwd"].get("anchors", 0) >= args.n][:args.stability]:
        alt, _ = counts(p, "fwd", seed=args.seed + 1000)
        if alt:
            stab[p] = {"seed_a": results[p]["fwd"]["pct_exactly_1"],
                       "seed_b": summarise(alt)["pct_exactly_1"]}

    json.dump({"params": vars(args), "results": results, "stability": stab},
              open(os.path.join(args.out, "uniqueness_survey.json"), "w"), indent=1)
    with open(os.path.join(args.out, "uniqueness_survey.csv"), "w") as fh:
        fh.write("relation,phase1_freq,fwd_anchors,fwd_pct1,fwd_pct_containment,"
                 "fwd_median,inv_anchors,inv_pct1,inv_median\n")
        for p, r in sorted(results.items(), key=lambda kv: -kv[1]["phase1_freq"]):
            f, v = r["fwd"], r["inv"]
            fh.write(f"{p},{r['phase1_freq']},{f.get('anchors',0)},{f.get('pct_exactly_1','')},"
                     f"{f.get('pct_unique_containment','')},{f.get('median','')},"
                     f"{v.get('anchors',0)},{v.get('pct_exactly_1','')},{v.get('median','')}\n")
    print(f"\nwrote {args.out}/uniqueness_survey.json and .csv  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
