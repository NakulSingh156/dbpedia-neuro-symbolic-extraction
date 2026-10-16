"""End-to-end dev run of approach N on the 23 dev descriptions: M1 (detect + keep) -> M2 anchor linking
(topic -> its Wikipedia title; named anchor -> Wikipedia title lookup) -> M4/M5 Wikidata query ->
M6 decision with tier. Compared with the oracle-parse outcome in occurrence/results/headroom_teaser.json.
DEV ONLY. -> results_pipeline_dev_<model>.json"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from generic.ir import Description            # noqa: E402
from generic.detect import keep              # noqa: E402
from generic.kb_wikidata import WikidataKB   # noqa: E402

model = sys.argv[1] if len(sys.argv) > 1 else "llama3.1:8b"
OCC = os.path.join(os.path.dirname(HERE), "occurrence")
by_id = {json.loads(l)["id"]: json.loads(l) for l in open(os.path.join(OCC, "all_sentences.jsonl"))}
gold = json.load(open(os.path.join(OCC, "results/headroom_teaser.json")))
cache = json.load(open(os.path.join(HERE, f"cache_detect_{model.replace(':', '_')}.json")))
kb = WikidataKB()

def decide(d, x):
    topic_title = x["topic"]
    anchor_title = topic_title if d.anchor.ref == "topic" else d.anchor.text
    q = kb.qid_for_title(anchor_title) or kb.qid_for_title(topic_title if d.anchor.text in topic_title else anchor_title)
    if not q or "wikidata" not in d.paths:
        return {"outcome": "UNRESOLVED", "anchor_qid": q, "answers": []}
    r = kb.values(q, d.paths["wikidata"], d.constraints.gender)
    n = len(r["known"])
    out = "GROUNDED" if n == 1 else "AMBIGUOUS" if n > 1 else "MISSING"
    return {"outcome": out, "anchor_qid": q, "answers": r["known"],
            "tier": ("schema_unique" if kb.schema_unique(d.paths["wikidata"]) else "data_unique") if out == "GROUNDED" else None}

rows, agree = [], 0
for g in gold:
    x = by_id[g["id"]]
    found = [d for d in (Description.from_dict(z) for z in cache[g["id"]]["found"]) if keep(d, x["sentence"])]
    # the detection for this gold description: same mention words if possible, else the first kept one
    pick = next((d for d in found if g["span"].split(" (")[0].lower() in d.mention.lower()), found[0] if found else None)
    res = decide(pick, x) if pick else {"outcome": "NOT-DETECTED", "answers": []}
    oracle = {"GROUNDED": "GROUNDED", "MISSING": "MISSING", "ANCHOR-NOT-IN-KB": "UNRESOLVED"}.get(g["kb_outcome"], g["kb_outcome"])
    same = res["outcome"] == oracle and sorted(res.get("answers", [])) == sorted(a[0] for a in g["kb_answers"])
    agree += same
    rows.append({"id": g["id"], "span": g["span"], "oracle": oracle, "oracle_answers": [a[0] for a in g["kb_answers"]],
                 "pipeline": res, "detected": pick.mention if pick else None,
                 "relations": pick.relation_phrases if pick else None, "same_as_oracle": same})
    print(f'{"=" if same else "≠"} {g["id"]} {g["span"][:36]:36s} oracle {oracle:10s} pipeline {res["outcome"]:12s} {res.get("answers", [])[:3]}')
lab = kb.labels(sorted({a for r in rows for a in r["pipeline"].get("answers", [])}))
for r in rows: r["pipeline"]["answer_labels"] = [lab.get(a, a) for a in r["pipeline"].get("answers", [])]
summ = {"model": model, "items": len(rows), "same_as_oracle": agree,
        "pipeline_outcomes": {k: sum(1 for r in rows if r["pipeline"]["outcome"] == k) for k in ("GROUNDED", "AMBIGUOUS", "MISSING", "UNRESOLVED", "NOT-DETECTED")},
        "wrong_grounding": [r["id"] for r in rows if r["pipeline"]["outcome"] == "GROUNDED" and r["pipeline"]["answers"] != r["oracle_answers"]]}
json.dump({"summary": summ, "rows": rows}, open(os.path.join(HERE, f"results_pipeline_dev_{model.replace(':', '_')}.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps(summ, indent=1))
