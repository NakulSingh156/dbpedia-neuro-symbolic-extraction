"""Detector metrics on NATURAL-DEV (45 biographies, labels_v0.json) for keep() versions, from the cached detections.
Sentence level: a sentence 'fires' if any kept detection exists; correct if genuine. -> natural/eval_natural.json"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
from generic.detect import keep           # noqa: E402
from generic.ir import Description        # noqa: E402
from generic.lexicon import expand        # noqa: E402
S = {json.loads(l)["nid"]: json.loads(l) for l in open(os.path.join(HERE, "sentences.jsonl"))}
cache = json.load(open(os.path.join(HERE, "detect_cache.json")))
lab = {o["nid"]: o for o in json.load(open(os.path.join(HERE, "labels_v0.json")))}
out = {}
for v in (2, 3):
    fired = gen_fired = 0
    for nid, s in S.items():
        ds = [Description.from_dict(x) for x in cache.get(nid, {}).get("found", [])]
        for d in ds:      # re-expand with the current lexicon (empty chains are no longer paths)
            d.paths = {kb: expand(d.relation_phrases, kb)[0] for kb in ("wikidata", "dbpedia") if expand(d.relation_phrases, kb)[0]}
        k = [d for d in ds if keep(d, s["sentence"], version=v)]
        if k:
            fired += 1; gen_fired += bool(lab.get(nid, {}).get("genuine"))
    n_gen = sum(o["genuine"] for o in lab.values())
    out[f"v{v}"] = {"sentences_fired": fired, "fired_genuine": gen_fired, "precision": round(gen_fired / fired, 3) if fired else None,
                    "recall_of_known_genuine": round(gen_fired / n_gen, 3), "known_genuine": n_gen}
    print(f"v{v}", out[f"v{v}"])
json.dump(out, open(os.path.join(HERE, "eval_natural.json"), "w"), indent=1)
