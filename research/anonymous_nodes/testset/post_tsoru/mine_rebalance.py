"""Rebalancing miner (19 Nov): fresh relational-description candidates for the outcomes the 100-row pool lacks
(KB_UNIQUE, KB_AMBIGUOUS). Candidates only — every row needs human verification.

People: humans with an English article, mid + head tiers (more text, more KB coverage), MD5-seeded, excluding the
45 natural-dev biographies, the 100 pool anchors and the controlled-set anchors.
Per article: scan sentences for possessive relational nouns ("his brother", "X's father"); drop mentions named right
after (NAMED_AFTER); query Wikidata with the lexicon path + gender; label:
  NAMED_IN_CONTEXT if a KB answer's label occurs in the article, else KB_UNIQUE / KB_AMBIGUOUS / KB_MISSING.
-> rebalance_candidates_2026-11-19.csv, rebalance_summary.json
"""
import csv, json, os, re, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "occurrence")); sys.path.insert(0, os.path.join(ROOT, "../../scripts"))
from generic.kb_wikidata import WikidataKB, WD, WDT   # noqa: E402
from generic.lexicon import expand, entry             # noqa: E402
from generic.detect import NAMED_AFTER                # noqa: E402
from sentence_split import split_sentences            # noqa: E402

PER_TIER, SEED = 60, "rebalance-v1"
TIERS = {"mid": (3, 17), "head": (18, 100000)}
SKIP = re.compile(r"^(references|notes|external links|see also|further reading|bibliography|works|filmography|"
                  r"discography|selected works|publications|sources|citations|honours|honors|awards|footnotes|gallery)", re.I)
PAT = re.compile(r"\b(?:[Hh]is|[Hh]er)\s+((?:(?:elder|older|younger|eldest|youngest|only|late|first|second|third|half|step)[-\s])?"
                 r"(?:brother|sister|father|mother|son|daughter|wife|husband|uncle|aunt|nephew|niece|cousin|grandfather|grandmother|"
                 r"grandson|granddaughter|father-in-law|mother-in-law|brother-in-law|sister-in-law|son-in-law|daughter-in-law))\b")
kb = WikidataKB()

excl = set()
for l in open(os.path.join(ROOT, "testset/natural/sentences.jsonl")): excl.add(json.loads(l)["qid"])
ev = json.load(open(os.path.join(HERE, "wikidata_slice_2026-11-19/wikidata_evidence_slice.json")))
excl |= {a["qid"] for a in ev["manifest"]["anchors"].values()}
for l in open(os.path.join(ROOT, "testset/prototype/cells.jsonl")): excl.add(json.loads(l)["anchor_qid"])

people = []
for tier, (lo, hi) in TIERS.items():
    rows = kb.sparql(f"""SELECT DISTINCT ?h ?t ?g WHERE {{ ?h <{WDT}P31> <{WD}Q5> . ?h <{WDT}P21> ?g .
        ?a <http://schema.org/about> ?h ; <http://schema.org/isPartOf> <https://en.wikipedia.org/> ; <http://schema.org/name> ?t .
        ?h <http://wikiba.se/ontology#sitelinks> ?n .
        FILTER(<http://www.w3.org/2001/XMLSchema#integer>(?n) >= {lo} && <http://www.w3.org/2001/XMLSchema#integer>(?n) <= {hi}) }}
        ORDER BY MD5(CONCAT(STR(?h), "{SEED}")) LIMIT {PER_TIER * 2}""")
    if not rows: raise RuntimeError("empty pool")
    picked = [(r["h"]["value"].rsplit("/", 1)[1], r["t"]["value"], r["g"]["value"].rsplit("/", 1)[1]) for r in rows]
    people += [(q, t, g, tier) for q, t, g in picked if q not in excl][:PER_TIER]
print("people", len(people), flush=True)

cands = []
for n, (q, title, g, tier) in enumerate(people, 1):
    j = kb.api("https://en.wikipedia.org/w/api.php", {"action": "query", "prop": "extracts|revisions", "explaintext": 1,
               "exsectionformat": "wiki", "rvprop": "ids", "redirects": 1, "titles": title})
    page = next(iter(j["query"]["pages"].values()))
    text = page.get("extract") or ""; rev = (page.get("revisions") or [{}])[0].get("revid")
    parts = re.split(r"\n(={2,6})\s*(.+?)\s*\1\n", text)
    body, skipping = [parts[0]], False
    for i in range(1, len(parts) - 2, 3):
        if len(parts[i]) == 2: skipping = bool(SKIP.match(parts[i + 1]))
        if not skipping: body.append(parts[i + 2])
    article = re.sub(r"\s*\n+\s*", " ", " ".join(body))
    seen = set()
    for s in split_sentences(article):
        for m in PAT.finditer(s):
            noun = m.group(1).lower().split()[-1].split("-")[-1] if "-in-law" not in m.group(1).lower() else m.group(1).lower().split()[-1]
            if NAMED_AFTER.match(s[m.end():]) or (q, noun) in seen: continue
            alts, gender = expand([noun], "wikidata")
            if not alts: continue
            seen.add((q, noun))
            r = kb.values(q, alts, gender)
            labs = kb.labels(r["known"]) if r["known"] else {}
            in_text = [k for k, v in labs.items() if v and v.split(",")[0] in article]
            outcome = ("NAMED_IN_CONTEXT" if in_text else "KB_UNIQUE" if len(r["known"]) == 1 else
                       "KB_AMBIGUOUS" if r["known"] else ("KB_UNKNOWN_VALUE" if r["unknown_values"] else "KB_MISSING"))
            cands.append({"item_id": f"RB-{len(cands)+1:03d}", "anchor": title, "anchor_qid": q, "tier": tier, "revision_id": rev,
                          "source_url": "https://en.wikipedia.org/wiki/" + title.replace(" ", "_"), "sentence": s, "target_span": m.group(0),
                          "relation": noun, "kb_answers": " | ".join(f"{labs.get(k, k)} [{k}]" for k in r["known"]),
                          "kb_unknown_values": r["unknown_values"], "answer_label_in_article": " | ".join(in_text),
                          "proposed_outcome": outcome, "status": "machine-proposed candidate; verify by hand"})
    if n % 20 == 0: print(f"  {n}/{len(people)} articles, {len(cands)} candidates", flush=True)
cols = list(cands[0].keys())
w = csv.DictWriter(open(os.path.join(HERE, "rebalance_candidates_2026-11-19.csv"), "w", newline=""), fieldnames=cols); w.writeheader(); w.writerows(cands)
summ = {"people": len(people), "candidates": len(cands), "by_outcome": dict(collections.Counter(c["proposed_outcome"] for c in cands)),
        "by_tier_outcome": {f"{a}/{b}": v for (a, b), v in collections.Counter((c["tier"], c["proposed_outcome"]) for c in cands).items()}}
json.dump(summ, open(os.path.join(HERE, "rebalance_summary.json"), "w"), indent=1)
print(json.dumps(summ, indent=1))
