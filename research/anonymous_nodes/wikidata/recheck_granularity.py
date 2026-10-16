"""Re-check the 16 Oct granularity merges with STRICT containment (kb_wikidata.ancestors(strict=True)).
The loose closure followed P361 transitively and could climb into alliances/organisations and back down.
-> results/granularity_strict.json"""
import json, os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from generic.kb_wikidata import WikidataKB   # noqa: E402
kb = WikidataKB()
F = [json.loads(l) for l in open(os.path.join(HERE, "results/paired_facts.jsonl"))]
loose = json.load(open(os.path.join(HERE, "results/ancestors_cache.json")))
res = {}
for side in ("wd", "dbp"):
    kept = dropped = 0; dropped_ex = []
    for r in F:
        a = r["wd_answer"] if side == "wd" else r.get("dbp_answer_qid")
        c = r["wd_correct"] if side == "wd" else r["dbp_correct"]
        b = r["obj_qid"]
        if c is not False or not a or not b: continue
        if not (b in loose.get(a, []) or a in loose.get(b, [])): continue      # not a loose granularity merge
        if b in kb.ancestors(a) or a in kb.ancestors(b): kept += 1
        else:
            dropped += 1; dropped_ex.append((r["rel"], a, b))
    res[side] = {"loose_merges": kept + dropped, "strict_kept": kept, "dropped": dropped, "dropped_examples": dropped_ex[:25]}
    print(side, {k: v for k, v in res[side].items() if k != "dropped_examples"}, flush=True)
json.dump(res, open(os.path.join(HERE, "results/granularity_strict.json"), "w"), indent=1)
