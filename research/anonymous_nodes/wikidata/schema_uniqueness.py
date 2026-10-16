"""Schema-unique vs data-unique (open-world check) -> results/schema_uniqueness.json

Schema-unique: the KB's schema says the relation has one value (Wikidata single-value or
single-best-value constraint on every mapped property; DBpedia owl:FunctionalProperty).
Data-unique: the KB happens to hold one value. For facts the KB grounds (unique / unique up to
containment), how often is the answer the text's entity, split by the two kinds?
Agreement = exact QID match or containment (results/ancestors_cache.json, from decompose_mismatches.py).
"""
import json, math, os, sys, collections, re
sys.argv = ["x", "--pause", "3"]
import survey_wikidata as S

F = [json.loads(l) for l in open("results/paired_facts.jsonl")]
MAP = json.load(open("results/mapping_used.json"))
anc = json.load(open("results/ancestors_cache.json"))
SINGLE = {"Q19474404": "single-value", "Q52060874": "single-best-value"}

def wilson(k, n, z=1.96):
    if not n: return [None, None]
    p = k / n; d = 1 + z*z/n; c = (p + z*z/(2*n)) / d; h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return [round(max(0, c - h), 3), round(min(1, c + h), 3)]

# Wikidata: which mapped properties carry a single-value constraint
props = sorted({p for r in F for p in MAP.get(r["rel"], {}).get("props", [])})
single = {}
for i in range(0, len(props), 40):
    vals = " ".join(f"<{S.WD}{p}>" for p in props[i:i + 40])
    rows = S.wq(f"""SELECT ?p ?c WHERE {{ VALUES ?p {{ {vals} }}
        ?p <http://www.wikidata.org/prop/P2302> ?st . ?st <http://www.wikidata.org/prop/statement/P2302> ?c .
        FILTER(?c IN (<{S.WD}Q19474404>, <{S.WD}Q52060874>)) }}""")
    assert rows is not None, "QLever failed"
    for x in rows:
        single[x["p"]["value"].rsplit("/", 1)[1]] = SINGLE[x["c"]["value"].rsplit("/", 1)[1]]
# a union of several properties (parent = father|mother) is not single-valued as a whole
wd_schema_unique = {rel for rel, m in MAP.items() if len(m.get("props", [])) == 1 and m["props"][0] in single}

# DBpedia: owl:FunctionalProperty in the ontology file
owl = open(os.path.join(os.path.dirname(__file__), "../../../data/dbpedia.owl")).read()
dbp_functional = set(re.findall(r'rdf:about="http://dbpedia.org/ontology/([^"]+)">\s*<rdf:type rdf:resource="http://www.w3.org/2002/07/owl#FunctionalProperty"', owl))

def agrees(a, b):
    return a == b or b in anc.get(a, []) or a in anc.get(b, [])

out = {"wd_props_checked": len(props), "wd_props_single_value": len(single),
       "dbp_functional_properties_in_ontology": len(dbp_functional)}
for kb in ("wd", "dbp"):
    su_rels = wd_schema_unique if kb == "wd" else dbp_functional
    cells = collections.defaultdict(lambda: {"grounded": 0, "agree": 0, "covered": 0, "unique": 0, "rels": collections.Counter()})
    for r in F:
        outc = r[f"{kb}_outcome"]
        a = r["wd_answer"] if kb == "wd" else r.get("dbp_answer_qid")
        cls = "schema_unique" if r["rel"] in su_rels else "data_unique"
        c = cells[cls]
        if outc != "none":
            c["covered"] += 1
            if outc.startswith("unique"): c["unique"] += 1
        if outc.startswith("unique") and a and r["obj_qid"]:
            c["grounded"] += 1; c["rels"][r["rel"]] += 1
            c["agree"] += agrees(a, r["obj_qid"])
    out[kb] = {}
    for cls, c in cells.items():
        out[kb][cls] = {"covered_facts": c["covered"],
                        "unique_given_covered_pct": round(100 * c["unique"] / c["covered"], 1) if c["covered"] else None,
                        "grounded_judged": c["grounded"],
                        "agree_exact_or_containment_pct": round(100 * c["agree"] / c["grounded"], 1) if c["grounded"] else None,
                        "agree_ci95": wilson(c["agree"], c["grounded"]),
                        "top_relations": c["rels"].most_common(8)}
# like-for-like: place-valued relations only (same convention issues on both sides)
PLACE = {"location", "locatedInArea", "isPartOf", "headquarter", "city", "region", "state", "district",
         "foundationPlace", "hometown", "residence", "ground", "county"}
lf = collections.Counter()
for r in F:
    if r["wd_outcome"].startswith("unique") and r["wd_answer"] and r["obj_qid"]:
        cls = "schema_unique_places" if r["rel"] in wd_schema_unique else ("data_unique_places" if r["rel"] in PLACE else None)
        if cls:
            lf[cls, "n"] += 1; lf[cls, "a"] += agrees(r["wd_answer"], r["obj_qid"])
out["wd_like_for_like_places"] = {cls: {"n": lf[cls, "n"], "agree_pct": round(100 * lf[cls, "a"] / lf[cls, "n"], 1),
                                        "ci95": wilson(lf[cls, "a"], lf[cls, "n"])}
                                  for cls in ("schema_unique_places", "data_unique_places")}
out["wd_single_value_props"] = single
out["wd_schema_unique_relations"] = sorted(wd_schema_unique)
out["dbp_functional_relations_seen"] = sorted({r["rel"] for r in F} & dbp_functional)
json.dump(out, open("results/schema_uniqueness.json", "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k not in ("wd_schema_unique_relations",)}, indent=1))
