"""Hand check (Claude, one pass, 19 Nov) of the 14 rebalancing candidates the miner flagged KB_UNIQUE / KB_AMBIGUOUS.
Aliases checked against every Wikidata alias in the article text. -> rebalance_verified_summary.json"""
import json, collections
V = {
 "RB-054": ("KB_UNIQUE", "father Moritz William, Duke of Saxe-Zeitz; no alias in the article"),
 "RB-066": ("KB_UNIQUE", "wife Haru Kagawa; not named in the article"),
 "RB-038": ("KB_AMBIGUOUS", "several brothers in Wikidata; the 1679 Scanian War context points to Christian V"),
 "RB-080": ("KB_AMBIGUOUS", "two sons in Wikidata (Samuel, Thomas)"),
 "RB-036": ("NAMED_IN_CONTEXT", "husband named in the article as 'Hiro' (Wikidata alias)"),
 "RB-067": ("NAMED_IN_CONTEXT", "mother named as 'Vedavalli' (Veda Jayaram)"),
 "RB-074": ("NAMED_IN_CONTEXT", "father named as Ismail Gasprinsky"),
 "RB-047": ("ANCHOR_ERROR", "'her son' = Katie Price's son, not the topic's"),
 "RB-068": ("ANCHOR_ERROR", "'her father's home' = the mother's father"),
 "RB-075": ("ANCHOR_ERROR", "'his sister' = the brother's sister (the topic herself)"),
 "RB-076": ("ANCHOR_ERROR", "'his daughter' = the brother's daughter"),
 "RB-009": ("NAMED_IN_SENTENCE", "'His mother was the horseback acrobat dancer Rocío Bermúdez'"),
 "RB-073": ("NAMED_IN_SENTENCE", "'Her mother was Zühre Gaspıralı'"),
 "RB-017": ("REGEX_SLIP", "'her mother' matched inside 'mother-in-law'"),
}
s = json.load(open("rebalance_summary.json"))
out = {"people": s["people"], "candidates": s["candidates"], "flagged_checked": len(V),
       "verified": sum(1 for v in V.values() if v[0] in ("KB_UNIQUE", "KB_AMBIGUOUS")),
       "by_outcome": dict(collections.Counter(v[0] for v in V.values())),
       "items": {k: {"verdict": v[0], "note": v[1]} for k, v in V.items()},
       "not_yet_checked": {"KB_MISSING": s["by_outcome"].get("KB_MISSING", 0), "NAMED_IN_CONTEXT": s["by_outcome"].get("NAMED_IN_CONTEXT", 0)}}
json.dump(out, open("rebalance_verified_summary.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in out.items() if k != "items"}, indent=1))
