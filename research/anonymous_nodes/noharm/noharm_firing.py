"""No-harm proxy on Text2KGBench (Tsoru decision 1): how often does the anonymous-node module fire on ORDINARY
benchmark sentences, and are those firings right? A module that rarely fires, and only on real unnamed entities,
cannot hurt ordinary extraction much. (The full no-harm check — end-to-end triple F1 with the module on — follows.)

Sample: seeded, stratified by domain — 300 DBpedia-WebNLG test sentences, 200 Wikidata-TekGen test sentences.
Detector: M1 + keep v3 + text-unknown rule (llama3.1:8b by default). Topic = the sentence's first capitalised name
(benchmark sentences have no article). -> noharm/firing_<model>.jsonl, firing_summary_<model>.json; firings hand-checked later.
"""
import glob, json, os, random, re, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from generic.detect import detect, keep   # noqa: E402
MODEL = sys.argv[1] if len(sys.argv) > 1 else "llama3.1:8b"
TAG = MODEL.replace("openrouter:", "").replace("/", "_").replace(":", "_")
rnd = random.Random(20)
def sample(half, n):
    files = sorted(glob.glob(os.path.expanduser(f"~/Text2KGBench/data/{half}/test/*.jsonl")))
    per = max(1, n // len(files)); out = []
    for f in files:
        rows = [json.loads(l) for l in open(f)]
        out += rnd.sample(rows, min(per, len(rows)))
    return out[:n]
items = [("dbpedia_webnlg", r) for r in sample("dbpedia_webnlg", 300)] + [("wikidata_tekgen", r) for r in sample("wikidata_tekgen", 200)]
OUT = os.path.join(HERE, f"firing_{TAG}.jsonl")
done = {json.loads(l)["id"] for l in open(OUT)} if os.path.exists(OUT) else set()
with open(OUT, "a") as f:
    for i, (half, r) in enumerate(items, 1):
        if r["id"] in done: continue
        m = re.match(r"\s*((?:[A-Z][\w'’.\-]*\s?){1,4})", r["sent"]); topic = (m.group(1).strip() if m else "the subject")
        found, err = detect(r["sent"], topic, r["sent"], model=MODEL)
        kept = [d for d in found if keep(d, r["sent"])]
        f.write(json.dumps({"half": half, "id": r["id"], "sent": r["sent"], "topic": topic, "err": err,
                            "raw": [d.mention for d in found], "kept": [{"mention": d.mention, "relations": d.relation_phrases} for d in kept]},
                           ensure_ascii=False) + "\n"); f.flush()
        if i % 25 == 0: print(f"  {i}/{len(items)}", flush=True)
rows = [json.loads(l) for l in open(OUT)]
summ = {h: {"sentences": sum(1 for r in rows if r["half"] == h), "fired": sum(1 for r in rows if r["half"] == h and r["kept"]),
            "raw_fired_before_filter": sum(1 for r in rows if r["half"] == h and r["raw"])} for h in ("dbpedia_webnlg", "wikidata_tekgen")}
for h in summ: summ[h]["fired_pct"] = round(100 * summ[h]["fired"] / summ[h]["sentences"], 1)
json.dump(summ, open(os.path.join(HERE, f"firing_summary_{TAG}.json"), "w"), indent=1)
print(json.dumps(summ, indent=1))
