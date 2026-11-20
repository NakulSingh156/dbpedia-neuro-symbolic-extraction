"""Paragraph-input setting (proposal for Tsoru): for candidates whose answer the article names somewhere, is the name
inside the SAME paragraph as the sentence? If not, a system given only the paragraph cannot read it off the text,
so the item becomes KB-groundable (KB_UNIQUE / KB_AMBIGUOUS) in the paragraph setting. -> paragraph_setting.json"""
import csv, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from generic.kb_wikidata import WikidataKB   # noqa: E402
kb = WikidataKB()
R = list(csv.DictReader(open(os.path.join(HERE, "rebalance_candidates_2026-11-19.csv"))))
ver = json.load(open(os.path.join(HERE, "rebalance_verified_summary.json")))["items"]
rows = []
for r in R:
    if r["proposed_outcome"] != "NAMED_IN_CONTEXT" and ver.get(r["item_id"], {}).get("verdict") != "NAMED_IN_CONTEXT":
        continue
    a = kb.api("https://en.wikipedia.org/w/api.php", {"action": "query", "prop": "extracts|revisions", "explaintext": 1, "exsectionformat": "wiki",
              "rvprop": "ids", "redirects": 1, "titles": r["anchor"]})
    text = next(iter(a["query"]["pages"].values())).get("extract", "")
    paras = [p for p in re.split(r"\n\s*\n|\n(?==)", text) if p.strip()]
    para = next((p for p in paras if r["sentence"][:60] in re.sub(r"\s*\n+\s*", " ", p)), "")
    qids = [x.split("[")[-1].rstrip("]") for x in r["kb_answers"].split(" | ") if "[" in x]
    names = []
    for q in qids:
        j = kb.api("https://www.wikidata.org/w/api.php", {"action": "wbgetentities", "ids": q, "props": "labels|aliases", "languages": "en"})
        e = j["entities"][q]; names += [e.get("labels", {}).get("en", {}).get("value", "")] + [x["value"] for x in e.get("aliases", {}).get("en", [])]
    in_para = any(n and n.split(",")[0] in para for n in names)
    rows.append({"item_id": r["item_id"], "anchor": r["anchor"], "target": r["target_span"], "kb_answers": r["kb_answers"], "paragraph_found": bool(para),
                 "name_in_same_paragraph": in_para,
                 "paragraph_setting_outcome": ("NAMED_IN_CONTEXT" if in_para else ("KB_UNIQUE" if len(qids) == 1 else "KB_AMBIGUOUS")) if para else "PARAGRAPH_NOT_FOUND"})
import collections
out = {"named_elsewhere_items": len(rows), "paragraph_setting": dict(collections.Counter(x["paragraph_setting_outcome"] for x in rows)), "rows": rows}
json.dump(out, open(os.path.join(HERE, "paragraph_setting.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))
for x in rows: print(" ", x["item_id"], x["anchor"][:22], "|", x["target"], "|", x["paragraph_setting_outcome"], "|", x["kb_answers"][:50])
