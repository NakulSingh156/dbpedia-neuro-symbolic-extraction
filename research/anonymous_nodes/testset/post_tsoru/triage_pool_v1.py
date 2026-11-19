"""Triage v1 of the 100-row pool against ANNOTATION_GUIDE_V1 and the 19 Nov evidence slice.
Machine-proposed labels for human review — NOT gold. -> pool_triage_v1_2026-11-19.csv + printed composition.

phenomenon:  U if the row states an unknown/anonymous identity, else R (relational description).
relation:    keyword map from relation_or_path to Wikidata properties (+ gender).
kb evidence: values of those properties on the anchor in the frozen slice, filtered by gender (P21 of the value);
             somevalue ("unknown value") claims counted separately.
outcome:     NAMED_IN_CONTEXT (article names it, per text_identity_status / notes) > TEXT_UNKNOWN (type U) >
             KB_UNIQUE / KB_AMBIGUOUS / KB_UNKNOWN_VALUE / KB_MISSING / ANCHOR_NOT_IN_KB / UNMAPPED_RELATION.
flags:       stress (disputed/speculative/conflicting/unreliable), multi (several targets), screening decision.
"""
import csv, json, re, collections, sys
SLICE = "wikidata_slice_2026-11-19"
pool = list(csv.DictReader(open("pool_v1_2026-11-19.csv")))
screen = {r["item_id"]: r for r in csv.DictReader(open("CANDIDATE_SCREENING_PASS_2026-11-07.csv"))}
ev = json.load(open(f"{SLICE}/wikidata_evidence_slice.json"))
anchors = ev["manifest"]["anchors"]; ents = ev["entities"]; sex = ev.get("target_sex_P21", {})
MALE, FEMALE = "Q6581097", "Q6581072"

REL = [  # (regex on relation_or_path + target_span, props, gender)
 (r"\bbrothers?\b|half-brother", ["P3373"], MALE), (r"\bsisters?\b|half-sister", ["P3373"], FEMALE),
 (r"\bsibling|\btwin", ["P3373"], None), (r"\bfather\b", ["P22"], MALE), (r"\bmother\b", ["P25"], FEMALE),
 (r"\bparent|parentage", ["P22", "P25"], None), (r"\bwife\b", ["P26"], FEMALE), (r"\bhusband\b", ["P26"], MALE),
 (r"\bspouse|married|marriage", ["P26"], None), (r"\bsons?\b", ["P40"], MALE), (r"\bdaughters?\b", ["P40"], FEMALE),
 (r"\bchild", ["P40"], None), (r"teacher", ["P1066"], None), (r"\bauthor|\bwrote\b|\bwriter", ["P50"], None),
 (r"\bartist|painter|created|creator|sculptor", ["P170"], None), (r"publisher", ["P123"], None),
 (r"employer|company", ["P108"], None),
]
U_PAT = re.compile(r"\bunknown\b|anonymous|unidentified|notname|not known|unnamed artist|unknown artist", re.I)
STRESS = re.compile(r"stress|disputed|speculat|competing|conflict|uncertain|unreliable|contested|conjecture|gossip|weak source|single-source|hypothes", re.I)
MULTI = re.compile(r"multiple|three|two |\bpair\b|parents|siblings|several|plural", re.I)

def values(qid, props):
    claims = ents.get(qid, {}).get("claims", {})
    vals, some = [], 0
    for p in props:
        for st in claims.get(p, []):
            sn = st.get("mainsnak", {})
            if sn.get("snaktype") == "somevalue": some += 1; continue
            v = sn.get("datavalue", {}).get("value", {})
            if isinstance(v, dict) and v.get("id"): vals.append(v["id"])
    return vals, some

out = []
for r in pool:
    iid = r["item_id"]; s = screen.get(iid, {})
    blob = " ".join([r["relation_or_path"], r["target_span"], s.get("case_family", "")]).lower()
    notes = " ".join([r["evidence_notes"], s.get("screening_reason", ""), r["text_identity_status"], r["relation_or_path"]])
    # the TEXT decides the type: the sentence / target span must state the identity is unknown (review notes do not count)
    phen = "U" if U_PAT.search(r["target_span"] + " " + r["sentence"]) and not r["text_identity_status"].startswith("context") else "R"
    # the target span decides the relation first ("One unnamed child" -> child), the review notes only as a fallback
    rel = (next(((p, g) for pat, p, g in REL if re.search(pat, r["target_span"].lower())), None)
           or next(((p, g) for pat, p, g in REL if re.search(pat, blob)), None))
    qid = anchors.get(iid, {}).get("qid")
    if r["text_identity_status"].startswith("context_resolvable"):
        outcome, cands, some = "NAMED_IN_CONTEXT", [], 0
    elif not qid:
        outcome, cands, some = "ANCHOR_NOT_IN_KB", [], 0
    elif not rel:
        outcome, cands, some = ("TEXT_UNKNOWN" if phen == "U" else "UNMAPPED_RELATION"), [], 0
    else:
        vals, some = values(qid, rel[0])
        other = {MALE: FEMALE, FEMALE: MALE}.get(rel[1])
        cands = [v for v in vals if not (other and other in sex.get(v, []))]
        if phen == "U":
            outcome = "TEXT_UNKNOWN"
        elif some and not cands:
            outcome = "KB_UNKNOWN_VALUE"
        else:
            outcome = "KB_UNIQUE" if len(cands) == 1 else "KB_AMBIGUOUS" if cands else "KB_MISSING"
    flags = [f for f, pat in (("stress", STRESS), ("multi", MULTI)) if pat.search(notes + " " + r["target_span"])]
    lab = ev.get("target_labels_en", {})
    out.append({"item_id": iid, "anchor": r["source_name"], "anchor_qid": qid or "", "revision_id": anchors.get(iid, {}).get("revision_id", ""),
                "sentence": r["sentence"], "target_span": r["target_span"], "phenomenon": phen,
                "relation_props": "|".join(rel[0]) if rel else "", "gender": {MALE: "male", FEMALE: "female"}.get(rel[1], "") if rel else "",
                "kb_candidates": " | ".join(f"{lab.get(c, c)} [{c}]" for c in cands), "kb_unknown_values": some,
                "proposed_outcome": outcome, "flags": " ".join(flags), "screening_decision": s.get("screening_decision", ""),
                "status": "machine-proposed; needs human annotation"})
cols = list(out[0].keys())
w = csv.DictWriter(open("pool_triage_v1_2026-11-19.csv", "w", newline=""), fieldnames=cols); w.writeheader(); w.writerows(out)
C = collections.Counter
print("phenomenon:", C(o["phenomenon"] for o in out))
print("outcome:", C(o["proposed_outcome"] for o in out).most_common())
print("outcome x phenomenon:", C((o["phenomenon"], o["proposed_outcome"]) for o in out).most_common())
print("stress:", sum("stress" in o["flags"] for o in out), "| multi:", sum("multi" in o["flags"] for o in out))
print("non-stress R by outcome:", C(o["proposed_outcome"] for o in out if o["phenomenon"] == "R" and "stress" not in o["flags"]).most_common())
print("screening x outcome:", C((o["screening_decision"], o["proposed_outcome"]) for o in out).most_common())
