"""Among the strict granularity merges (16 Oct decomposition), how many join two DIFFERENT sovereign states?
Those are leaks (alliance items list members under P17), not granularity. -> results/granularity_country_leaks.json"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from generic.kb_wikidata import WikidataKB   # noqa: E402
kb = WikidataKB()
F = [json.loads(l) for l in open(os.path.join(HERE, "results/paired_facts.jsonl"))]
loose = json.load(open(os.path.join(HERE, "results/ancestors_cache.json")))
out = {}
for side in ("wd", "dbp"):
    leaks, kept = [], 0
    for r in F:
        a = r["wd_answer"] if side == "wd" else r.get("dbp_answer_qid"); b = r["obj_qid"]
        c = r["wd_correct"] if side == "wd" else r["dbp_correct"]
        if c is not False or not a or not b or not (b in loose.get(a, []) or a in loose.get(b, [])): continue
        if not (b in kb.ancestors(a) or a in kb.ancestors(b)): continue
        if kb.is_country(a) and kb.is_country(b): leaks.append((r["rel"], a, b))
        else: kept += 1
    lab = kb.labels(sorted({x for l in leaks for x in l[1:]}))
    out[side] = {"strict_merges": kept + len(leaks), "country_country_leaks": len(leaks), "clean_granularity": kept,
                 "leaks": [(rel, lab[a], lab[b]) for rel, a, b in leaks]}
    print(side, {k: v for k, v in out[side].items() if k != "leaks"}, out[side]["leaks"][:10], flush=True)
json.dump(out, open(os.path.join(HERE, "results/granularity_country_leaks.json"), "w"), indent=1, ensure_ascii=False)
