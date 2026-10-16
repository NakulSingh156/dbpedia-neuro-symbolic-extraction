"""Hand grading of results/headroom_teaser.json -> results/headroom_summary.json (Claude, one pass).

Per LLM answer: ABSTAIN (UNKNOWN, or a restatement such as "Arthur Winter's brother") · TEXT (correct,
and the entity is named or inferable elsewhere in the abstract) · CORRECT (correct, not in the text) ·
PLAUSIBLE (names something reasonable the KB lacks; not verified) · WRONG (names a wrong entity).
"""
import json, collections
#        (qwen, llama)
CODES = [("ABSTAIN", "ABSTAIN"), ("ABSTAIN", "ABSTAIN"), ("ABSTAIN", "ABSTAIN"), ("ABSTAIN", "PLAUSIBLE"),
         ("ABSTAIN", "ABSTAIN"), ("ABSTAIN", "PLAUSIBLE"), ("ABSTAIN", "ABSTAIN"), ("ABSTAIN", "ABSTAIN"),
         ("ABSTAIN", "ABSTAIN"), ("ABSTAIN", "ABSTAIN"), ("ABSTAIN", "ABSTAIN"), ("TEXT", "TEXT"),
         ("TEXT", "TEXT"), ("TEXT", "TEXT"), ("ABSTAIN", "ABSTAIN"), ("ABSTAIN", "ABSTAIN"),
         ("ABSTAIN", "TEXT"), ("TEXT", "TEXT"), ("CORRECT", "CORRECT"), ("ABSTAIN", "ABSTAIN"),
         ("ABSTAIN", "ABSTAIN"), ("TEXT", "TEXT"), ("TEXT", "TEXT")]
H = json.load(open("results/headroom_teaser.json"))
assert len(H) == len(CODES)
kb = collections.Counter(r["kb_outcome"] for r in H)
out = {"descriptions": len(H), "kb_outcomes_oracle_parse": dict(kb), "llm": {}}
for i, m in enumerate(("qwen2.5:7b", "llama3.1:8b")):
    out["llm"][m] = dict(collections.Counter(c[i] for c in CODES))
grounded = [k for k, r in enumerate(H) if r["kb_outcome"] == "GROUNDED"]
out["kb_grounded_but_both_llms_abstain"] = [H[k]["span"] + " / " + H[k]["anchor"] for k in grounded if CODES[k] == ("ABSTAIN", "ABSTAIN")]
out["kb_missing_but_llm_named"] = [(H[k]["span"], H[k]["anchor"], CODES[k]) for k, r in enumerate(H)
                                   if r["kb_outcome"] != "GROUNDED" and "ABSTAIN" not in CODES[k][1:] + CODES[k][:1] or
                                   (r["kb_outcome"] != "GROUNDED" and CODES[k] != ("ABSTAIN", "ABSTAIN"))]
for r, c in zip(H, CODES): r["grade"] = {"qwen2.5:7b": c[0], "llama3.1:8b": c[1]}
json.dump(H, open("results/headroom_teaser.json", "w"), indent=1, ensure_ascii=False)
json.dump(out, open("results/headroom_summary.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False))
