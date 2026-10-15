#!/usr/bin/env python3
"""
UNNAMED-ENTITY PROXY — does a benchmark contain entities its sentence never names?

For every entity-valued gold triple, check whether the subject and object names
appear in the sentence. An entity whose name is absent (no full-name match and
under half of its content tokens present) is a candidate "unnamed" mention: a
pronoun, a description ("her husband"), or an alias the check can't see.

This is a PROXY with known false positives (aliases, abbreviations, transliteration),
so a random sample of hits is written out for manual inspection and the inspected
precision is reported next to the raw rate.
"""
import collections, glob, json, os, random, re, sys, unicodedata

BENCH = os.path.expanduser("~/Text2KGBench/data")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
STOP = {"the", "of", "and", "a", "an", "in", "on", "for", "to", "de", "la", "le", "von", "van", "der", "da"}
LIT = re.compile(r'^\s*"|^-?[\d.,]+$|^\d{4}-\d{2}-\d{2}|^\d{1,2} \w+ \d{4}$|^\d{4}$')


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


def label(ent, dataset):
    s = ent.replace("_", " ") if dataset == "dbpedia_webnlg" else ent
    return re.sub(r"\s*\([^)]*\)\s*$", "", s).strip()


def named(ent, sent, dataset):
    l, s = norm(label(ent, dataset)), " " + norm(sent) + " "
    if not l:
        return True
    if " " + l + " " in s:
        return True
    toks = [t for t in l.split() if t not in STOP and len(t) > 1]
    if not toks:
        return True
    return sum(1 for t in toks if " " + t + " " in s) / len(toks) >= 0.5


def run(dataset, seed=1):
    rows = []
    for f in sorted(glob.glob(f"{BENCH}/{dataset}/ground_truth/*.jsonl")):
        for line in open(f):
            r = json.loads(line)
            rows.append(r)
    mentions = unnamed = 0
    sent_with = 0
    examples = []
    for r in rows:
        hit = False
        for t in r.get("triples", []):
            for role in ("sub", "obj"):
                e = str(t[role])
                if LIT.match(e):
                    continue
                mentions += 1
                if not named(e, r["sent"], dataset):
                    unnamed += 1
                    hit = True
                    examples.append({"id": r["id"], "role": role, "entity": e, "rel": t["rel"], "sent": r["sent"]})
        sent_with += hit
    random.Random(seed).shuffle(examples)
    os.makedirs(OUT, exist_ok=True)
    with open(f"{OUT}/{dataset}_unnamed_sample.jsonl", "w") as fh:
        for x in examples[:60]:
            fh.write(json.dumps(x, ensure_ascii=False) + "\n")
    res = {"dataset": dataset, "sentences": len(rows), "entity_mentions": mentions,
           "unnamed_mentions": unnamed, "pct_unnamed_mentions": round(100 * unnamed / max(mentions, 1), 2),
           "sentences_with_unnamed": sent_with, "pct_sentences_with_unnamed": round(100 * sent_with / max(len(rows), 1), 2)}
    json.dump(res, open(f"{OUT}/{dataset}_unnamed_proxy.json", "w"), indent=1)
    return res


if __name__ == "__main__":
    for ds in ("dbpedia_webnlg", "wikidata_tekgen"):
        print(run(ds))
