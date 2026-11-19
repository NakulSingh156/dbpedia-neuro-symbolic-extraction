"""Human annotation sheet v1 (ANNOTATION_GUIDE_V1 §6) for the pool + accepted rebalancing rows.
Machine-proposed labels are deliberately NOT shown (guide §8: pre-annotations only after the human labels are saved).
KB evidence shown = frozen-slice values for the relation, gender-filtered (no outcome guess shown).
-> annotation_sheet_v1_<annotator>.csv"""
import csv, json, sys
ann = sys.argv[1] if len(sys.argv) > 1 else "nakul"
tri = list(csv.DictReader(open("pool_triage_v1_2026-11-19.csv")))
pool = {r["item_id"]: r for r in csv.DictReader(open("pool_v1_2026-11-19.csv"))}
cols = ["item_id", "source_url", "revision_id", "anchor", "anchor_qid", "sentence", "context", "target_span", "kb_evidence_frozen_19nov",
        # --- to fill (guide §4–§6) ---
        "phenomenon_R_or_U", "relation_path", "outcome_label", "gold_target_qid_or_anon_id", "candidate_qids", "anonymous_status",
        "flags", "world_identity_and_source", "include_yes_no", "notes"]
rows = []
for t in tri:
    p = pool[t["item_id"]]
    rows.append({"item_id": t["item_id"], "source_url": p["source_url_or_id"], "revision_id": t["revision_id"], "anchor": t["anchor"],
                 "anchor_qid": t["anchor_qid"], "sentence": p["sentence"], "context": p["context"], "target_span": p["target_span"],
                 "kb_evidence_frozen_19nov": t["kb_candidates"] + (f" | unknown-value claims: {t['kb_unknown_values']}" if str(t["kb_unknown_values"]) not in ("0", "") else "")})
w = csv.DictWriter(open(f"annotation_sheet_v1_{ann}.csv", "w", newline=""), fieldnames=cols); w.writeheader(); w.writerows(rows)
print(len(rows), "rows ->", f"annotation_sheet_v1_{ann}.csv")
