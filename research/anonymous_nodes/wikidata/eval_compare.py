"""Evaluate generic/compare.py on the 60 hand-coded residual mismatches (wikidata/results/disagreement_coding.json).
Wanted: C (same fact, other convention) and G (missed granularity) merged; K (real difference) never merged;
X (our extraction error) reported separately. -> results/compare_eval.json"""
import json, os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from generic.compare import Comparator   # noqa: E402

F = [json.loads(l) for l in open(os.path.join(HERE, "results/paired_facts.jsonl"))]
idx = json.load(open(os.path.join(HERE, "results/disagreement_sample_idx.json")))
codes = json.load(open(os.path.join(HERE, "results/disagreement_coding.json")))["codes"]
cmp = Comparator()
rows, tab = [], collections.Counter()
for kb in ("wd", "dbp"):
    for i, code in zip(idx[kb], codes[kb]):
        r = F[i]
        a = r["wd_answer"] if kb == "wd" else r["dbp_answer_qid"]
        merged, rule = cmp.same(a, r["obj_qid"])
        tab[code, merged] += 1
        rows.append({"kb": kb, "i": i, "rel": r["rel"], "text": r["obj_qid"], "kb_answer": a, "code": code, "merged": merged, "rule": rule,
                     "text_is_disambiguation": cmp.is_disambiguation(r["obj_qid"])})
out = {"by_code": {c: {"merged": tab[c, True], "kept_apart": tab[c, False]} for c in "CGKX"},
       "rules_fired": dict(collections.Counter(r["rule"] for r in rows if r["merged"])),
       "false_merges_on_K": [r for r in rows if r["code"] == "K" and r["merged"]],
       "text_side_disambiguation_links": sum(r["text_is_disambiguation"] for r in rows),
       "rows": rows}
json.dump(out, open(os.path.join(HERE, "results/compare_eval.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))
