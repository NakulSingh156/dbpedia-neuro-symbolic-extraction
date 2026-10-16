"""Held-out natural set, mining step (METHODOLOGY.md §6.2). Candidates only: every candidate is verified by hand.

People: humans with an English article, 15 per popularity tier (tail/mid/head, same global cuts as the
controlled set), MD5-seeded, EXCLUDING the 2,000 Phase-1 abstract topics and every controlled-set anchor.
Text: full article (lead + body, list-like sections dropped), canonical splitter. Every sentence goes through
(a) occurrence/scan.py and (b) the M1 detector (Llama-3.1-8B + keep filter). Candidates = union.
-> testset/natural/sentences.jsonl, candidates.jsonl, mining_summary.json
"""
import json, os, re, sys, time, requests
from urllib.parse import unquote
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "occurrence")); sys.path.insert(0, os.path.join(ROOT, "../../scripts"))
from generic.kb_wikidata import WikidataKB, WD, WDT   # noqa: E402
from generic.detect import detect, keep               # noqa: E402
from scan import scan                                 # noqa: E402
from sentence_split import split_sentences            # noqa: E402

PER_TIER, SEED, MODEL = 15, "natural-v0", "llama3.1:8b"
TIERS = {"tail": (1, 2), "mid": (3, 17), "head": (18, 100000)}
SKIP = re.compile(r"^(references|notes|external links|see also|further reading|bibliography|works|filmography|"
                  r"discography|selected works|publications|sources|citations|honours|honors|awards|footnotes|gallery)", re.I)
OUT = os.path.join(HERE, "natural"); os.makedirs(OUT, exist_ok=True)
kb = WikidataKB()

exclude = {json.loads(l)["abstract_uri"].rsplit("/", 1)[1] for l in open(os.path.join(ROOT, "occurrence/all_sentences.jsonl"))}
exclude = {unquote(x).replace("_", " ") for x in exclude}
for f in ("cells.jsonl", "controlled_proto.jsonl"):
    p = os.path.join(HERE, "prototype", f)
    if os.path.exists(p):
        exclude |= {json.loads(l)["anchor"] for l in open(p)}

people = []
for tier, (lo, hi) in TIERS.items():
    rows = kb.sparql(f"""SELECT DISTINCT ?h ?t WHERE {{ ?h <{WDT}P31> <{WD}Q5> .
        ?a <http://schema.org/about> ?h ; <http://schema.org/isPartOf> <https://en.wikipedia.org/> ; <http://schema.org/name> ?t .
        ?h <http://wikiba.se/ontology#sitelinks> ?n .
        FILTER(<http://www.w3.org/2001/XMLSchema#integer>(?n) >= {lo} && <http://www.w3.org/2001/XMLSchema#integer>(?n) <= {hi}) }}
        ORDER BY MD5(CONCAT(STR(?h), "{SEED}")) LIMIT 60""")
    if not rows: raise RuntimeError(f"empty pool {tier}")
    picked = [(r["h"]["value"].rsplit("/", 1)[1], r["t"]["value"]) for r in rows if r["t"]["value"] not in exclude][:PER_TIER]
    people += [(q, t, tier) for q, t in picked]
print(f"people {len(people)} (excluded {len(exclude)} known titles)", flush=True)

sents = []
for q, title, tier in people:
    j = kb.api("https://en.wikipedia.org/w/api.php", {"action": "query", "prop": "extracts", "explaintext": 1,
               "exsectionformat": "wiki", "redirects": 1, "titles": title})
    text = next(iter(j["query"]["pages"].values())).get("extract") or ""
    parts = re.split(r"\n(={2,6})\s*(.+?)\s*\1\n", text)
    chunks, skipping = [("lead", parts[0])], False
    for i in range(1, len(parts) - 2, 3):
        if len(parts[i]) == 2: skipping = bool(SKIP.match(parts[i + 1]))
        if not skipping: chunks.append(("body", parts[i + 2]))
    k = 0
    for src, txt in chunks:
        for s in split_sentences(re.sub(r"\s*\n+\s*", " ", txt)):
            sents.append({"nid": f"n{len(sents):05d}", "qid": q, "title": title, "tier": tier, "source": src, "k": k, "sentence": s}); k += 1
with open(os.path.join(OUT, "sentences.jsonl"), "w") as f:
    for s in sents: f.write(json.dumps(s, ensure_ascii=False) + "\n")
print(f"sentences {len(sents)}", flush=True)

ctx = {}
for s in sents: ctx.setdefault(s["qid"], []).append(s["sentence"])
cands, n_scan, n_det = [], 0, 0
CACHE = os.path.join(OUT, "detect_cache.json")
dcache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
for i, s in enumerate(sents):
    hits = [h["span"] for h in scan(s["sentence"])]
    if s["nid"] not in dcache:
        # context = the 4 sentences before + the sentence (article-length context is too long for an 8B model)
        window = " ".join(ctx[s["qid"]][max(0, s["k"] - 4): s["k"] + 1])
        found, err = detect(s["sentence"], s["title"], window, model=MODEL)
        dcache[s["nid"]] = {"found": [json.loads(d.to_json()) for d in found], "err": err}
        if i % 25 == 0: json.dump(dcache, open(CACHE, "w"), ensure_ascii=False); print(f"  detected {i}/{len(sents)}", flush=True)
    from generic.ir import Description
    kept = [d for d in (Description.from_dict(x) for x in dcache[s["nid"]]["found"]) if keep(d, s["sentence"])]
    n_scan += bool(hits); n_det += bool(kept)
    if hits or kept:
        cands.append({**s, "scan_hits": hits, "detector": [{"mention": d.mention, "anchor": d.anchor.text,
                      "relations": d.relation_phrases, "gender": d.constraints.gender} for d in kept]})
json.dump(dcache, open(CACHE, "w"), ensure_ascii=False)
with open(os.path.join(OUT, "candidates.jsonl"), "w") as f:
    for c in cands: f.write(json.dumps(c, ensure_ascii=False) + "\n")
summ = {"people": len(people), "sentences": len(sents), "scan_hit_sentences": n_scan, "detector_sentences": n_det,
        "candidates_union": len(cands), "both": sum(1 for c in cands if c["scan_hits"] and c["detector"])}
json.dump(summ, open(os.path.join(OUT, "mining_summary.json"), "w"), indent=1)
print(json.dumps(summ, indent=1))
