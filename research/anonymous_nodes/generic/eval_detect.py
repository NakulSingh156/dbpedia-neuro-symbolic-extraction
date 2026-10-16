"""Dev evaluation of M1 (detect.py): the 23 real descriptions of occurrence/results/headroom_teaser.json
(hand-written gold paths) + negative sentences from the 300-sentence sample that carry no O-REL/O-DESC
label. These are DEV items (used while designing) - never report them as test results.
-> results/detect_dev.json"""
import json, os, sys, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from generic.detect import detect   # noqa: E402

OCC = os.path.join(os.path.dirname(HERE), "occurrence")
A = [json.loads(l) for l in open(os.path.join(OCC, "all_sentences.jsonl"))]
by_id = {x["id"]: x for x in A}
abstract = {}
for x in A: abstract.setdefault(x["abstract_uri"], []).append(x["sentence"])
gold = json.load(open(os.path.join(OCC, "results/headroom_teaser.json")))
labels = json.load(open(os.path.join(OCC, "labels_sample_300.json")))["items"]
neg_ids = [it["id"] for it in labels if not any(l["type"] in ("O-REL", "O-DESC", "O-PRON") for l in it["labels"])]
neg_ids = random.Random(5).sample(neg_ids, 60)
model = next((a for a in sys.argv[1:] if not a.startswith("--")), "qwen2.5:7b")

def paths_key(alts):
    return {tuple(tuple(h.props) for h in p) for p in alts}

from generic.ir import Description   # noqa: E402
CACHE = os.path.join(HERE, f"cache_detect_{model.replace(':', '_')}.json")
disk = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
cache = {}
def run(sid):
    """Raw detections are cached on disk (prompt changes => delete the cache file)."""
    if sid not in cache:
        x = by_id[sid]
        if sid in disk:
            found = [Description.from_dict(d) for d in disk[sid]["found"]]; err = disk[sid]["err"]
        else:
            found, err = detect(x["sentence"], x["topic"], " ".join(abstract[x["abstract_uri"]]), model=model)
            disk[sid] = {"found": [json.loads(d.to_json()) for d in found], "err": err}
            json.dump(disk, open(CACHE, "w"), ensure_ascii=False)
        from generic.detect import keep
        cache[sid] = ([d for d in found if keep(d, x["sentence"])] if FILTER else found, err)
    return cache[sid]
FILTER = "--no-filter" not in sys.argv

GW = {"Q6581097": "male", "Q6581072": "female", None: None}
rows, hit, path_ok, anchor_ok = [], 0, 0, 0
for g in gold:
    g["gender_word"] = GW.get(g["gender"], g["gender"])
    found, err = run(g["id"])
    gp = {tuple((h,) if isinstance(h, str) else tuple(h) for h in p) for p in g["paths"]}  # gold: one prop string per hop
    match = next((d for d in found if d.paths.get("wikidata") and paths_key(d.paths["wikidata"]) & gp
                  and d.constraints.gender == g["gender_word"]), None)
    loose = match or next((d for d in found if any(w in d.mention.lower() for w in g["span"].lower().split()[-2:])), None)
    hit += bool(loose); path_ok += bool(match)
    a_ok = bool(match) and (match.anchor.text.lower() in g["anchor"].lower() or g["anchor"].lower().startswith(match.anchor.text.lower().split(" (")[0]))
    anchor_ok += a_ok
    rows.append({"id": g["id"], "gold_span": g["span"], "gold_paths": g["paths"], "detected": [json.loads(d.to_json()) for d in found],
                 "found": bool(loose), "path_correct": bool(match), "anchor_correct": a_ok, "error": err})
from generic.detect import keep   # noqa: E402
fp_sent, fp_kept, fp_items = 0, 0, []
for sid in neg_ids:
    found, err = run(sid)
    if found:
        fp_sent += 1; fp_items.append({"id": sid, "sentence": by_id[sid]["sentence"], "detected": [d.mention for d in found],
                                       "kept": [d.mention for d in found]})
    fp_kept += bool(found)
out = {"model": model, "positives": len(gold), "found": hit, "path_correct": path_ok, "anchor_correct_given_path": anchor_ok,
       "negatives": len(neg_ids), "negatives_with_a_detection": fp_sent, "negatives_with_a_kept_detection": fp_kept, "false_positive_examples": fp_items[:15], "rows": rows}
out["filter"] = FILTER
json.dump(out, open(os.path.join(HERE, f"results_detect_dev_{model.replace(':', '_')}{'' if FILTER else '_nofilter'}.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in out.items() if k not in ("rows",)}, indent=1, ensure_ascii=False))
for r in rows:
    print(("OK  " if r["path_correct"] else "FND " if r["found"] else "MISS"), r["id"], r["gold_span"][:40], "->",
          [(d["mention"], d["relation_phrases"], d["anchor"]["text"]) for d in r["detected"]][:3])
