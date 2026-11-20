"""Write the dry-run decisions for the 100-row pool as an anonymous-node KG (generic/writer.py) and validate it
by parsing with rdflib. -> pool_graph_<model>.ttl, plus graph statistics."""
import csv, json, os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from generic.writer import serialize   # noqa: E402
TAG = sys.argv[1] if len(sys.argv) > 1 else ""
dry = list(csv.DictReader(open(os.path.join(HERE, f"pilot_dryrun_{TAG}.csv" if TAG else "pilot_dryrun_2026-11-19.csv"))))
tri = {r["item_id"]: r for r in csv.DictReader(open(os.path.join(HERE, "pool_triage_v1_2026-11-19.csv")))}
pool = {r["item_id"]: r for r in csv.DictReader(open(os.path.join(HERE, "pool_v1_2026-11-19.csv")))}
man = json.load(open(os.path.join(HERE, "wikidata_slice_2026-11-19/capture_manifest.json")))
SINGLE = {"P22", "P25", "P19", "P20", "P36"}
items = []
for r in dry:
    t, p = tri[r["item_id"]], pool[r["item_id"]]
    props = [x for x in t["relation_props"].split("|") if x]
    rev = man["anchors"].get(r["item_id"], {}).get("revision_id")
    title = man["anchors"].get(r["item_id"], {}).get("title", "")
    cands = [c.split("[")[-1].rstrip("]") for c in t["kb_candidates"].split(" | ") if "[" in c]
    items.append({"item_id": r["item_id"], "anchor_qid": t["anchor_qid"], "props": props, "outcome": r["N_outcome"],
                  "answers": r["N_answers"].split(), "span": p["target_span"], "anchor_label": title, "gender": t["gender"],
                  "tier": "schema_unique" if len(props) == 1 and props[0] in SINGLE else "data_unique",
                  "revision_url": f"https://en.wikipedia.org/w/index.php?oldid={rev}", "slice_sha": man["evidence_slice_sha256"][:16],
                  "method": "N (M1 detector + frozen-slice KB + decision rules)", "candidates": cands if r["N_outcome"] in ("AMBIGUOUS", "TEXT_UNKNOWN") else []})
ttl, n = serialize(items)
path = os.path.join(HERE, f"pool_graph{'_' + TAG if TAG else ''}.ttl"); open(path, "w").write(ttl)
import rdflib
g = rdflib.Graph(); g.parse(path, format="turtle")
NEF = rdflib.Namespace("https://w3id.org/nef/anon#")
anon = set(g.subjects(rdflib.RDF.type, NEF.AnonymousEntity))
st = collections.Counter(str(o).split("#")[-1] for s in anon for o in g.objects(s, NEF.status))
print(json.dumps({"facts_written": n, "triples": len(g), "anonymous_nodes": len(anon), "anonymous_by_status": dict(st),
                  "grounded_edges": sum(1 for it in items if it["outcome"] == "GROUNDED")}, indent=1))
print(path)
