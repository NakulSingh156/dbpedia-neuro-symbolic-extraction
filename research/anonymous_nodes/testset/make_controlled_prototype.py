"""Controlled-set generator, PROTOTYPE (METHODOLOGY.md §6.1). Not the frozen test set.

1. Anchors = random English Wikipedia articles (list=random, uniform) that are humans in Wikidata.
2. For each anchor and kinship noun, Wikidata decides the gold type: unique / ambiguous / none,
   plus the grounding tier (schema-unique or data-unique) and the anchor's popularity (sitelinks).
3. Each unique item also yields a SIMULATED-MISSING twin: the answer is masked at query time
   (GrailQAbility-style deletion), so the truth stays known for lenient scoring.
4. Description surface forms (possessive / of-phrase / pronoun with a context sentence) are written
   from templates; LLM paraphrase and human checking come later.
-> testset/prototype/controlled_proto.jsonl, summary.json
"""
import json, os, random, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from generic.kb_wikidata import WikidataKB, WD, WDT   # noqa: E402
from generic.lexicon import expand                     # noqa: E402

N_ANCHORS, SEED = 60, 21
NOUNS_BY_ANCHOR_GENDER = {"male": ["father", "mother", "wife", "brother", "sister", "son", "daughter"],
                          "female": ["father", "mother", "husband", "brother", "sister", "son", "daughter"]}
kb = WikidataKB()
rnd = random.Random(SEED)

# 1. random humans with an English article
humans = {}
batch = 0
while len(humans) < N_ANCHORS and batch < 40:
    batch += 1
    j = kb.api("https://en.wikipedia.org/w/api.php", {"action": "query", "list": "random", "rnnamespace": 0,
               "rnlimit": 50, "_seed": f"{SEED}-{batch}"})       # _seed only varies the cache key
    titles = [r["title"] for r in j["query"]["random"]]
    j2 = kb.api("https://en.wikipedia.org/w/api.php", {"action": "query", "prop": "pageprops",
                "ppprop": "wikibase_item", "titles": "|".join(titles)})
    qids = {p.get("pageprops", {}).get("wikibase_item"): p["title"] for p in j2["query"]["pages"].values()
            if p.get("pageprops", {}).get("wikibase_item")}
    vals = " ".join(f"<{WD}{q}>" for q in qids)
    rows = kb.sparql(f"""SELECT ?h ?g ?n WHERE {{ VALUES ?h {{ {vals} }} ?h <{WDT}P31> <{WD}Q5> .
                         OPTIONAL {{ ?h <{WDT}P21> ?g }} OPTIONAL {{ ?h <http://wikiba.se/ontology#sitelinks> ?n }} }}""")
    for r in rows:
        q = r["h"]["value"].rsplit("/", 1)[1]
        g = {"Q6581097": "male", "Q6581072": "female"}.get(r.get("g", {}).get("value", "").rsplit("/", 1)[-1])
        if g and q not in humans:
            humans[q] = {"title": qids[q], "gender": g, "sitelinks": int(r.get("n", {}).get("value", 0))}
humans = dict(list(humans.items())[:N_ANCHORS])
print(f"random batches {batch} | humans {len(humans)}", flush=True)

# 2. gold per anchor x noun
items = []
for q, h in humans.items():
    for noun in NOUNS_BY_ANCHOR_GENDER[h["gender"]]:
        alts, g = expand([noun], "wikidata")
        r = kb.values(q, alts, g)
        n = len(r["known"])
        gold_type = "unique" if n == 1 else "ambiguous" if n > 1 else "none"
        base = {"anchor_qid": q, "anchor": h["title"], "anchor_gender": h["gender"], "sitelinks": h["sitelinks"],
                "noun": noun, "paths": [[hop.props for hop in p] for p in alts], "gender": g,
                "tier": "schema_unique" if kb.schema_unique(alts) else "data_unique",
                "unknown_values": r["unknown_values"]}
        items.append({**base, "gold_type": gold_type, "gold": r["known"], "simulated": False})
        if gold_type == "unique":
            items.append({**base, "gold_type": "none", "gold": [], "simulated": True, "hidden_truth": r["known"]})

# 3. popularity tiers by sitelink tertiles over anchors
cuts = sorted(h["sitelinks"] for h in humans.values())
t1, t2 = cuts[len(cuts) // 3], cuts[2 * len(cuts) // 3]
lab = kb.labels(sorted({x for it in items for x in it["gold"] + it.get("hidden_truth", [])}))
for i, it in enumerate(items):
    it["pop_tier"] = "tail" if it["sitelinks"] <= t1 else "mid" if it["sitelinks"] <= t2 else "head"
    pron = "His" if it["anchor_gender"] == "male" else "Her"
    it["surface"] = {"possessive": f"{it['anchor']}'s {it['noun']}",
                     "of_phrase": f"the {it['noun']} of {it['anchor']}",
                     "pronoun": [f"{it['anchor']} is the subject of this article.", f"{pron} {it['noun']}"]}
    it["gold_labels"] = [lab.get(x, x) for x in it["gold"]]
    it["id"] = f"proto-{i:04d}"

os.makedirs(os.path.join(HERE, "prototype"), exist_ok=True)
with open(os.path.join(HERE, "prototype/controlled_proto.jsonl"), "w") as f:
    for it in items: f.write(json.dumps(it, ensure_ascii=False) + "\n")
c = collections.Counter((it["gold_type"], it["simulated"]) for it in items)
summ = {"anchors": len(humans), "items": len(items), "sitelink_cuts": [t1, t2],
        "by_type": {f"{k[0]}{'_simulated' if k[1] else ''}": v for k, v in c.items()},
        "by_tier": dict(collections.Counter(it["tier"] for it in items if not it["simulated"])),
        "by_pop": {f"{a}/{b}": v for (a, b), v in sorted(collections.Counter((it["pop_tier"], it["gold_type"]) for it in items if not it["simulated"]).items())},
        "by_noun": {n: dict(collections.Counter(it["gold_type"] for it in items if it["noun"] == n and not it["simulated"]))
                    for n in ["father", "mother", "wife", "husband", "brother", "sister", "son", "daughter"]}}
json.dump(summ, open(os.path.join(HERE, "prototype/summary.json"), "w"), indent=1)
print(json.dumps(summ, indent=1))
