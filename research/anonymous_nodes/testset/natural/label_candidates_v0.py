"""Hand verification (Claude, one pass, 17 Oct) of natural/candidates.jsonl (216 sentences, 45 biographies).
GENUINE[i] = candidate index whose sentence holds a relational description of a non-topic entity that is not named
in that sentence (flags: ne = named elsewhere in the article, pl = plural group).
DET[i] = what the detector did on that genuine case: ok (right relation), wrong (wrong relation), miss.
Every other candidate = no genuine case (named in the sentence, the topic itself, organisations, events, lists).
These 45 biographies become NATURAL-DEV: tuning on them is allowed; held-out numbers need new biographies.
-> natural/labels_v0.json"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
G = {  # index: (flags, detector)
 2: ((), "ok"), 5: (("ne", "pl"), "ok"), 10: ((), "ok"), 20: ((), "ok"), 21: (("pl",), "miss"), 29: ((), "ok"),
 40: ((), "ok"), 41: (("ne",), "ok"), 44: (("ne", "pl"), "ok"), 45: (("ne",), "ok"), 46: (("ne",), "ok"), 51: ((), "ok"),
 52: ((), "ok"), 53: (("pl",), "ok"), 54: ((), "ok"), 55: ((), "miss"), 56: ((), "ok"), 57: ((), "ok"), 60: ((), "ok"),
 69: (("ne", "pl"), "ok"), 72: (("ne", "pl"), "ok"), 83: ((), "ok"), 84: ((), "ok"), 85: ((), "ok"), 88: (("ne", "pl"), "ok"),
 89: (("ne", "pl"), "ok"), 94: (("pl",), "ok"), 95: (("ne",), "ok"), 99: ((), "ok"), 103: (("pl",), "miss"), 104: ((), "ok"),
 106: ((), "ok"),
 109: (("ne", "pl"), "ok"), 111: ((), "ok"), 116: (("ne",), "ok"), 117: (("ne",), "miss"), 118: (("ne",), "ok"),
 122: ((), "miss"), 124: (("ne",), "ok"), 125: (("ne",), "ok"), 128: (("ne",), "ok"), 130: (("pl",), "wrong"),
 135: (("pl",), "miss"), 143: ((), "ok"), 144: ((), "miss"), 149: ((), "ok"), 151: (("ne",), "ok"), 153: (("ne",), "ok"),
 170: (("pl",), "ok"), 171: ((), "ok"), 172: (("pl",), "ok"), 174: ((), "ok"), 175: ((), "miss"), 183: (("ne",), "ok"),
 189: ((), "ok"), 195: ((), "ok"), 197: (("ne",), "ok"), 209: ((), "miss"), 215: (("pl",), "ok"),
}
C = [json.loads(l) for l in open(os.path.join(HERE, "candidates.jsonl"))]
out = []
for i, c in enumerate(C):
    g = G.get(i)
    out.append({"i": i, "nid": c["nid"], "genuine": bool(g), "flags": list(g[0]) if g else [], "detector": g[1] if g else None,
                "detector_fired": bool(c["detector"]), "scan_fired": bool(c["scan_hits"])})
json.dump(out, open(os.path.join(HERE, "labels_v0.json"), "w"), indent=1)
gen = [o for o in out if o["genuine"]]
print({"candidates": len(out), "genuine": len(gen), "detector_ok": sum(o["detector"] == "ok" for o in gen),
       "detector_wrong": sum(o["detector"] == "wrong" for o in gen), "detector_miss": sum(o["detector"] == "miss" for o in gen),
       "scan_found_genuine": sum(o["scan_fired"] for o in gen),
       "detector_sentences": sum(o["detector_fired"] for o in out),
       "detector_sentences_genuine": sum(o["detector_fired"] and o["genuine"] for o in out)})
