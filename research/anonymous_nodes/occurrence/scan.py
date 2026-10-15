"""Stage 2: high-recall scan of all_sentences.jsonl for relational descriptions
("his wife", "the band's drummer", "the founder of ...") -> results/scan_hits.jsonl.

Every hit is checked by hand afterwards (scan_verified.json). A hit whose noun is
immediately followed by a capitalised name ("his brother Antonio", "his wife, Mary")
is pre-tagged `apposition` = named in the sentence, which the guidelines exclude.
"""
import json, re, os

NOUNS = """father mother son daughter brother sister wife husband spouse widow widower child children parent parents
nephew niece uncle aunt cousin grandfather grandmother grandson granddaughter grandchild grandchildren
father-in-law mother-in-law son-in-law daughter-in-law brother-in-law sister-in-law stepfather stepmother stepson
half-brother half-sister twin fiancé fiancée partner heir ancestor descendant
successor predecessor teacher mentor student pupil protégé coach captain founder co-founder owner chairman
president leader manager director producer drummer guitarist singer vocalist bassist keyboardist frontman
member bandmate teammate colleague employer patron sponsor
capital headquarters subsidiary sequel prequel spin-off adaptation remake debut label publisher author creator
architect designer builder mayor governor bishop king queen prince princess ruler regent""".split()
NOUN_RE = "|".join(sorted({re.escape(n) for n in NOUNS} | {re.escape(n) + "s" for n in NOUNS}, key=len, reverse=True))
DET = r"(?:[Hh]is|[Hh]er|[Ii]ts|[Tt]heir|[A-Z][\w.\-]*(?:'s|’s|')|the \w+(?:'s|’s))"
MOD = r"(?:(?:[a-z][\w\-]*|\d+)\s+){0,2}"
PATS = [
    ("possessive", re.compile(rf"\b{DET}\s+{MOD}(?P<n>{NOUN_RE})\b")),
    ("of_phrase", re.compile(rf"\b[Tt]he\s+{MOD}(?P<n>{NOUN_RE})\s+of\b")),
]
APPOS = re.compile(r"^,?\s+(?:the\s+)?[A-Z][a-z]")

def scan(sentence):
    hits = []
    for kind, p in PATS:
        for m in p.finditer(sentence):
            hits.append({"kind": kind, "span": m.group(0), "noun": m.group("n"), "start": m.start(),
                         "apposition": bool(APPOS.match(sentence[m.end():]))})
    return hits

if __name__ == "__main__":
    A = [json.loads(l) for l in open("all_sentences.jsonl")]
    os.makedirs("results", exist_ok=True)
    n_s = n_h = n_app = 0
    with open("results/scan_hits.jsonl", "w") as f:
        for x in A:
            h = scan(x["sentence"])
            if not h: continue
            n_s += 1; n_h += len(h); n_app += sum(k["apposition"] for k in h)
            f.write(json.dumps({"id": x["id"], "topic": x["topic"], "sentence": x["sentence"], "hits": h}, ensure_ascii=False) + "\n")
    print(f"sentences {len(A)} | with hits {n_s} | hits {n_h} | pre-tagged apposition {n_app}")
