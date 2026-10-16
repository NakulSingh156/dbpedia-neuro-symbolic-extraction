"""Hand verification of density-probe hits (results/density_hits.jsonl) -> results/density_summary.json.

Every hit sentence was read (Claude, one pass). GENUINE = holds a relational description of a
non-topic entity that is not named in that sentence. Flags: ne = named elsewhere in the same text,
fic = fictional (film plot or soap character), pl = plural group, kb = referent likely has a KB entry.
All other hits: named in the sentence (apposition, copula), a predicate on the topic ("the son of X",
"the founder of X"), debuts/positions, generic groups, or a reference to the topic itself.
"""
import json, math, collections

G = {  # did: (flags...)
 # DBpedia abstracts
 "d00071": (), "d01515": ("ne", "kb"), "d01810": ("kb",), "d01811": ("kb",),
 # article lead sections
 "d00066": (), "d00145": ("ne",), "d00147": ("kb",), "d00494": ("fic",),
 # article bodies
 "d00088": ("pl",), "d00132": (), "d00531": ("ne", "fic"), "d00646": ("ne",), "d00649": (), "d00652": ("ne",),
 "d00705": (), "d00716": (), "d00751": ("ne",), "d00761": ("ne",), "d00774": ("ne",), "d00798": ("pl",),
 "d00822": ("ne", "pl"), "d00847": ("pl",), "d00952": ("kb",), "d00961": ("ne",), "d01081": ("ne",),
 "d01284": ("kb",), "d01493": ("pl", "kb"), "d01508": ("kb",), "d01525": ("ne", "kb"), "d01527": (),
 "d01547": (), "d01773": (), "d01779": ("kb",), "d01821": (),
 "d01054": ("fic",), "d01251": ("fic",), "d01295": ("fic",), "d01296": ("fic",), "d01331": ("fic",), "d01400": ("fic",),
}

def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z*z/n; c = (p + z*z/(2*n)) / d; h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return [round(max(0, c - h), 4), round(min(1, c + h), 4)]

S = [json.loads(l) for l in open("results/density_sentences.jsonl")]
hits = {json.loads(l)["did"] for l in open("results/density_hits.jsonl")}
assert set(G) <= hits
src_of = {s["did"]: s["source"] for s in S}
n_src = collections.Counter(s["source"] for s in S)
persons = len({s["topic"] for s in S})
out = {"persons": persons, "sentences": dict(n_src), "hit_sentences": collections.Counter(src_of[d] for d in hits)}
for src in ("dbpedia_abstract", "article_lead", "article_body"):
    ids = [d for d in G if src_of[d] == src]
    n = n_src[src]
    def cnt(pred):
        k = sum(1 for d in ids if pred(G[d])); return {"k": k, "per_100_sentences": round(100 * k / n, 2), "ci95": wilson(k, n), "per_person": round(k / persons, 2)}
    out[src] = {"genuine_any": cnt(lambda f: True),
                "non_fiction": cnt(lambda f: "fic" not in f),
                "non_fiction_not_named_elsewhere": cnt(lambda f: "fic" not in f and "ne" not in f),
                "non_fiction_not_named_kb_likely": cnt(lambda f: "fic" not in f and "ne" not in f and "kb" in f),
                "named_elsewhere_share": round(sum("ne" in G[d] for d in ids) / len(ids), 2) if ids else None}
json.dump(out, open("results/density_summary.json", "w"), indent=1)
print(json.dumps(out, indent=1))
