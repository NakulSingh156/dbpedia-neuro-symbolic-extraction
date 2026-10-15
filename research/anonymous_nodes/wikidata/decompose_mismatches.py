"""Split KB-vs-text answer mismatches (paired_facts.jsonl) into granularity vs genuine disagreement
-> results/correctness_decomposition.json.

Granularity = the KB's answer and the text's entity contain one another on Wikidata
(P131/P17/P361/P276/P706/P749, transitive), e.g. a town vs its county. Pairs whose query failed
are reported as `unchecked`, never counted as disagreement.

QLever times out when both ends of a transitive path come from VALUES (it materialises and sorts the
whole closure), so each entity's ancestor set is fetched once from a bound subject and the pair is
compared in Python. Ancestors are cached in results/ancestors_cache.json, so a rerun resumes.
"""
import json, os, sys, collections
sys.argv = ["x", "--pause", "5"]
import survey_wikidata as S

F = [json.loads(l) for l in open("results/paired_facts.jsonl")]
P = S.path(S.CONT_WD)
BATCH = 10

def mismatches(kb):
    out = []
    for r in F:
        a = r["wd_answer"] if kb == "wd" else r.get("dbp_answer_qid")
        c = r["wd_correct"] if kb == "wd" else r["dbp_correct"]
        if c is False and a and r["obj_qid"]:
            out.append((r, a, r["obj_qid"]))
    return out

CACHE = "results/ancestors_cache.json"
anc = json.load(open(CACHE)) if os.path.exists(CACHE) else {}

def ancestors(q):
    if q not in anc:
        rows = S.wq(f"SELECT DISTINCT ?b WHERE {{ <{S.WD}{q}> ({P})+ ?b }}")
        if rows is None:
            return None
        anc[q] = sorted({x["b"]["value"][len(S.WD):] for x in rows})
        if len(anc) % 10 == 0:
            json.dump(anc, open(CACHE, "w"))
    return set(anc[q])

def contained(prs):
    hit, failed = set(), set()
    for i, (_, a, b) in enumerate(prs, 1):
        A, B = ancestors(a), ancestors(b)
        if A is None or B is None:
            failed.add((a, b))
        elif b in A or a in B:
            hit.add((a, b))
        if i % 25 == 0 or i == len(prs):
            print(f"   {i}/{len(prs)} pairs | contained {len(hit)} | unchecked {len(failed)} | cached {len(anc)}", flush=True)
    json.dump(anc, open(CACHE, "w"))
    return hit, failed

res = {}
for kb in ("dbp", "wd"):
    prs = mismatches(kb)
    print(kb, len(prs), "mismatches", flush=True)
    hit, failed = contained(prs)
    judged = sum(1 for r in F if (r["wd_correct"] if kb == "wd" else r["dbp_correct"]) is not None)
    match = sum(1 for r in F if (r["wd_correct"] if kb == "wd" else r["dbp_correct"]) is True)
    gran = sum(1 for _, a, b in prs if (a, b) in hit)
    unchecked = sum(1 for _, a, b in prs if (a, b) in failed)
    res[kb] = {"judged": judged, "exact_match": match, "mismatch": len(prs), "granularity": gran,
               "unchecked": unchecked, "genuine_disagreement": len(prs) - gran - unchecked,
               "exact_pct": round(100 * match / judged, 1),
               "consistent_pct": round(100 * (match + gran) / judged, 1),
               "granularity_by_relation": collections.Counter(r["rel"] for r, a, b in prs if (a, b) in hit).most_common(8),
               "disagreement_by_relation": collections.Counter(r["rel"] for r, a, b in prs
                                                               if (a, b) not in hit and (a, b) not in failed).most_common(8)}
    print(kb, {k: v for k, v in res[kb].items() if "by_relation" not in k}, flush=True)
json.dump(res, open("results/correctness_decomposition.json", "w"), indent=1)
