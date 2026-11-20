"""Pool v2 = the 100-row pool + tonight's hand-checked rebalancing items (20 Nov). Candidates for annotation, not gold.
Adds: 32 verified KB-missing relational descriptions, 2 KB-unique + 2 KB-ambiguous (article input), 5 KB-unique in the
paragraph setting, and named-in-context items. -> pool_v2_candidates.csv, pool_v2_composition.json"""
import csv, json, collections
tri = list(csv.DictReader(open("pool_triage_v1_2026-11-19.csv")))
rb = {r["item_id"]: r for r in csv.DictReader(open("rebalance_candidates_2026-11-19.csv"))}
miss = json.load(open("rebalance_missing_verified.json"))["keep_items"]
ver = json.load(open("rebalance_verified_summary.json"))["items"]
para = {r["item_id"]: r for r in json.load(open("paragraph_setting.json"))["rows"]}
rows = []
for t in tri:
    rows.append({"item_id": t["item_id"], "source": "pool_v1", "phenomenon": t["phenomenon"], "outcome_article": t["proposed_outcome"],
                 "outcome_paragraph": t["proposed_outcome"], "stress": "stress" in t["flags"], "check": t["screening_decision"]})
for iid in miss:
    rows.append({"item_id": iid, "source": "rebalance", "phenomenon": "R", "outcome_article": "KB_MISSING", "outcome_paragraph": "KB_MISSING",
                 "stress": False, "check": "hand-checked 20 Nov" + (" (named-elsewhere check pending)" if miss[iid] == "ctx?" else "")})
for iid, v in ver.items():
    if v["verdict"] in ("KB_UNIQUE", "KB_AMBIGUOUS", "NAMED_IN_CONTEXT"):
        po = para.get(iid, {}).get("paragraph_setting_outcome", v["verdict"])
        rows.append({"item_id": iid, "source": "rebalance", "phenomenon": "R", "outcome_article": v["verdict"], "outcome_paragraph": po,
                     "stress": False, "check": "hand-checked 19 Nov"})
for iid, p in para.items():
    if iid in ver: continue
    rows.append({"item_id": iid, "source": "rebalance", "phenomenon": "R", "outcome_article": "NAMED_IN_CONTEXT",
                 "outcome_paragraph": p["paragraph_setting_outcome"], "stress": False, "check": "alias/paragraph check 20 Nov"})
w = csv.DictWriter(open("pool_v2_candidates.csv", "w", newline=""), fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
QUOTA = {"NAMED_IN_CONTEXT": 20, "KB_UNIQUE": 20, "KB_AMBIGUOUS": 15, "KB_MISSING": 20, "TEXT_UNKNOWN": 20}
def comp(key):
    c = collections.Counter(r[key] for r in rows if not r["stress"])
    return {k: {"available": c.get(k, 0), "quota": QUOTA[k]} for k in QUOTA}
out = {"rows": len(rows), "stress_excluded": sum(r["stress"] for r in rows),
       "by_phenomenon": dict(collections.Counter(r["phenomenon"] for r in rows)),
       "article_setting": comp("outcome_article"), "paragraph_setting": comp("outcome_paragraph")}
json.dump(out, open("pool_v2_composition.json", "w"), indent=1)
print(json.dumps(out, indent=1))
