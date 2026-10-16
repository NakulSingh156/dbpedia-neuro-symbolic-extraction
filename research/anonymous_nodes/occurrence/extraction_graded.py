"""Hand grading of results/extraction_mode.json (Claude, one pass) -> results/extraction_summary.json.

What happened to the unnamed entity in each model's triples:
  NAMED_OK     a correct canonical name (from the text or knowledge)
  NAMED_PLAUS  a name that is plausible but unverified (KB has nothing)
  NAMED_WRONG  a wrong entity put in its place (hallucinated / misattributed identity)
  PHRASE       the description kept as a node string ("brother_of_Arthur_Henry_Winter", "wife") - a junk entity
  FLATTENED    the entity disappears into an attribute of the anchor ("fatherOccupation: lawyer")
  DROPPED      the fact about it is not extracted at all
"""
import json, collections
#                 qwen          llama
CODES = [("PHRASE", "PHRASE"),            # 00506 his brother
         ("PHRASE", "PHRASE"),            # 00951 father-in-law of Isaac N. Deadrick
         ("FLATTENED", "NAMED_PLAUS"),    # 00964 namesake nephew ("nephew: notable architect" / "Carlo Zucchi (architect)")
         ("PHRASE", "PHRASE"),            # 01649 its ruler
         ("PHRASE", "PHRASE"),            # 01816 his wife ("wife" / "wife_of_George_Hyde")
         ("DROPPED", "DROPPED"),          # 01981 founder of Merida (inner description)
         ("PHRASE", "PHRASE"),            # 01981 grandson of the founder of Merida
         ("FLATTENED", "FLATTENED"),      # 02054 son of a financial secretary
         ("FLATTENED", "FLATTENED"),      # 02126 his daughter drowned
         ("PHRASE", "FLATTENED"),         # 02127 another of his daughters
         ("FLATTENED", "FLATTENED"),      # 02528 his dead son (qwen also makes the diarist the builder)
         ("PHRASE", "NAMED_OK"),          # 03186 her father('s quiz show)
         ("NAMED_OK", "NAMED_OK"),        # 03360 her son
         ("NAMED_OK", "NAMED_OK"),        # 03360 her grandson
         ("FLATTENED", "PHRASE"),         # 03715 his father was a lawyer
         ("PHRASE", "PHRASE"),            # 03772 the wife of Guilhem
         ("PHRASE", "NAMED_OK"),          # 03773 his brother-in-law (llama infers Guilhem)
         ("NAMED_OK", "NAMED_OK"),        # 04298 his brother (Asher, from text)
         ("NAMED_OK", "PHRASE"),          # 04484 its genus
         ("PHRASE", "PHRASE"),            # 04769 a daimyo of the Akizuki clan
         ("NAMED_WRONG", "PHRASE"),       # 04770 his mother (qwen: mother = "the fourth head of Yonezawa")
         ("DROPPED", "DROPPED"),          # 05017 like his father, he was a JP
         ("NAMED_OK", "NAMED_OK")]        # 05035 his father (named in text)
E = json.load(open("results/extraction_mode.json")); assert len(E) == len(CODES)
out = {"descriptions": len(E), "by_model": {}}
for i, m in enumerate(("qwen2.5:7b", "llama3.1:8b")):
    c = collections.Counter(x[i] for x in CODES)
    lost = c["PHRASE"] + c["FLATTENED"] + c["DROPPED"]
    out["by_model"][m] = {**c, "entity_lost_or_junk": lost, "entity_lost_or_junk_pct": round(100 * lost / len(E), 1)}
gr = [k for k, e in enumerate(E) if e["kb_outcome"] == "GROUNDED"]
out["kb_grounded_items"] = len(gr)
out["kb_grounded_but_llm_not_named_ok"] = {m: sum(1 for k in gr if CODES[k][i] != "NAMED_OK") for i, m in enumerate(("qwen2.5:7b", "llama3.1:8b"))}
for e, c in zip(E, CODES): e["grade"] = {"qwen2.5:7b": c[0], "llama3.1:8b": c[1]}
json.dump(E, open("results/extraction_mode.json", "w"), indent=1, ensure_ascii=False)
json.dump(out, open("results/extraction_summary.json", "w"), indent=1)
print(json.dumps(out, indent=1))
