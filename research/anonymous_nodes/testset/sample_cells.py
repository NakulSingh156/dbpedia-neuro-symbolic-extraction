"""Per-cell sampler for the controlled set (METHODOLOGY.md §6.1), Wikidata side. Prototype quotas.

Cells = relation noun x popularity tier x gold type (unique / ambiguous / none) + simulated-none twins.
Popularity tiers use GLOBAL sitelink quantiles of humans with an English article (2,154,452 on
16 Oct; P33=2, P95=18, P99=38): tail <=2, mid 3-17, head >=18 (top 5%).
Anchors are drawn reproducibly: ORDER BY MD5(STR(?h) + seed) over humans with an enwiki article in the
tier — "has" pools (the path exists) fill unique/ambiguous cells, "any" pools fill natural none cells.
-> testset/prototype/cells.jsonl, cells_summary.json
"""
import json, os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from generic.kb_wikidata import WikidataKB, WD, WDT   # noqa: E402
from generic.lexicon import expand                     # noqa: E402

SEED, QUOTA, POOL = "cells-v0", 5, 60
TIERS = {"tail": (1, 2), "mid": (3, 17), "head": (18, 100000)}
NOUNS = ["father", "mother", "husband", "wife", "brother", "sister", "son", "daughter", "nephew", "grandfather"]
kb = WikidataKB()

def pool(tier, alts=None):
    lo, hi = TIERS[tier]
    has = ""
    if alts:
        has = "{ " + " } UNION { ".join(f"?h {WikidataKB._path(p)} ?x" for p in alts) + " }"
    q = f"""SELECT DISTINCT ?h ?t WHERE {{ ?h <{WDT}P31> <{WD}Q5> .
        ?a <http://schema.org/about> ?h ; <http://schema.org/isPartOf> <https://en.wikipedia.org/> ; <http://schema.org/name> ?t .
        ?h <http://wikiba.se/ontology#sitelinks> ?n .
        FILTER(<http://www.w3.org/2001/XMLSchema#integer>(?n) >= {lo} && <http://www.w3.org/2001/XMLSchema#integer>(?n) <= {hi}) {has} }}
        ORDER BY MD5(CONCAT(STR(?h), "{SEED}")) LIMIT {POOL}"""
    rows = kb.sparql(q)
    # QLever silently returns nothing for numeric FILTERs on xsd:int sitelinks unless cast (16 Oct);
    # an empty pool is therefore treated as a bug, never as "no anchors".
    if not rows:
        raise RuntimeError(f"empty anchor pool for tier={tier} has={bool(alts)} — check the query")
    return [(r["h"]["value"].rsplit("/", 1)[1], r["t"]["value"]) for r in rows]

items, tried = [], collections.Counter()
for noun in NOUNS:
    alts, g = expand([noun], "wikidata")
    tier_flag = "schema_unique" if kb.schema_unique(alts) else "data_unique"
    for tier in TIERS:
        need = {"unique": QUOTA, "ambiguous": QUOTA, "none": QUOTA}
        for source in ("has", "any"):
            for q, title in pool(tier, alts if source == "has" else None):
                if source == "has" and need["unique"] <= 0 and need["ambiguous"] <= 0: break
                if source == "any" and need["none"] <= 0: break
                tried[noun, tier, source] += 1
                r = kb.values(q, alts, g)
                n = len(r["known"])
                t = "unique" if n == 1 else "ambiguous" if n > 1 else "none"
                if (source == "any") != (t == "none") or need[t] <= 0:
                    continue
                need[t] -= 1
                base = {"noun": noun, "pop_tier": tier, "anchor_qid": q, "anchor": title, "gender": g,
                        "tier": tier_flag, "paths": [[h.props for h in p] for p in alts], "unknown_values": r["unknown_values"]}
                items.append({**base, "gold_type": t, "gold": r["known"], "simulated": False})
                if t == "unique":
                    items.append({**base, "gold_type": "none", "gold": [], "simulated": True, "hidden_truth": r["known"]})
        print(f"{noun:12s} {tier:5s} filled: " + ", ".join(f"{k} {QUOTA - v}/{QUOTA}" for k, v in need.items()), flush=True)

lab = kb.labels(sorted({x for it in items for x in it["gold"] + it.get("hidden_truth", [])}))
os.makedirs(os.path.join(HERE, "prototype"), exist_ok=True)
with open(os.path.join(HERE, "prototype/cells.jsonl"), "w") as f:
    for i, it in enumerate(items):
        it["id"] = f"cell-{i:04d}"; it["gold_labels"] = [lab.get(x, x) for x in it["gold"] + it.get("hidden_truth", [])]
        f.write(json.dumps(it, ensure_ascii=False) + "\n")
fill = collections.Counter((it["noun"], it["pop_tier"], it["gold_type"]) for it in items if not it["simulated"])
summ = {"items": len(items), "real": sum(1 for i in items if not i["simulated"]), "simulated_none": sum(1 for i in items if i["simulated"]),
        "cells_full": sum(1 for v in fill.values() if v >= QUOTA), "cells_total": len(NOUNS) * len(TIERS) * 3,
        "underfilled": sorted(f"{n}/{t}/{g}: {fill.get((n, t, g), 0)}" for n in NOUNS for t in TIERS
                              for g in ("unique", "ambiguous", "none") if fill.get((n, t, g), 0) < QUOTA),
        "anchors_checked": {f"{k[0]}/{k[1]}/{k[2]}": v for k, v in tried.items()}}
json.dump(summ, open(os.path.join(HERE, "prototype/cells_summary.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in summ.items() if k != "anchors_checked"}, indent=1, ensure_ascii=False))
