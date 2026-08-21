#!/usr/bin/env python3
"""
AUDIT PACK — turn a Phase-1 run into something two mentors can actually fill in.

The raw audit_sample.tsv asks one question, "correct?", which conflates two
independent failure modes:

    FAITHFUL   does the source sentence actually state this?
    LINKED     do the URIs point at the right DBpedia entities?

A triple can be perfectly faithful and still mislinked (`Auron_(comics)` vs
`Auron_(comicsCharacter)`), and the two have completely different fixes — one is
a Node-1 problem, the other a Node-2 problem. Collapsing them into one column
throws away the signal that tells us which to work on.

Precision is then FAITHFUL and LINKED together, and we also get each rate
separately at no extra cost to the auditor.

Emits CSV (imports cleanly into Google Sheets, which is where two people can
actually work at once) plus a short instruction sheet.

Usage
-----
    python scripts/make_audit_pack.py --run phase1_pilot4
"""
import argparse, csv, json, os, random

ap = argparse.ArgumentParser()
ap.add_argument("--run", required=True, help="phase1_<tag> directory")
ap.add_argument("--n", type=int, default=200)
ap.add_argument("--seed", type=int, default=7)
args = ap.parse_args()

rows = [json.loads(l) for l in open(os.path.join(args.run, "triples.jsonl"))]
sample = random.Random(args.seed).sample(rows, min(args.n, len(rows)))

out_csv = os.path.join(args.run, "audit_pack.csv")
with open(out_csv, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["id", "faithful (y/n/?)", "linked (y/n/na)", "notes",
                "subject", "predicate", "object", "status",
                "source sentence", "source abstract"])
    for i, r in enumerate(sample, 1):
        w.writerow([f"T{i:03d}", "", "", "",
                    r["sub"], r["rel"], r["obj"], r["status"],
                    r["sentence"], r["abstract_uri"]])

open(os.path.join(args.run, "AUDIT_INSTRUCTIONS.md"), "w").write(f"""# Audit instructions — {args.run}

{len(sample)} triples sampled at random from {len(rows)} extracted from 100
Wikipedia abstracts. Two columns to fill per row; everything else is context.

## Column 1 — `faithful`: does the source sentence state this?

Judge the triple **against the sentence only**. Not against what you know, not
against what Wikipedia says elsewhere.

* `y` — the sentence supports it
* `n` — it does not, or contradicts it
* `?` — genuinely ambiguous (please add a note)

Read the predicate charitably: `location` for "is situated in" is a `y`.
Judge the claim, not the wording.

## Column 2 — `linked`: do the URIs point at the right entities?

* `y` — subject and object resolve to the entities the sentence means
* `n` — at least one points somewhere else (a namesake, a disambiguation page,
  the wrong sense)
* `na` — the object is a literal (a date, number or quoted string), so there is
  nothing to link. Subject-only judgement in that case.

A triple can be `faithful=y, linked=n`. That distinction is the point of
separating the columns — please do not merge them.

## What we compute

    precision       = faithful=y AND linked in (y, na)
    faithfulness    = faithful=y
    linking accuracy = linked=y  (over rows where linked != na)

## Please do not

Fix or rewrite anything. A wrong triple with a note is worth more to us than a
corrected one — we need the error rate, and the notes tell us which stage to
fix.
""")
print(f"wrote {out_csv}  ({len(sample)} rows)")
print(f"wrote {os.path.join(args.run, 'AUDIT_INSTRUCTIONS.md')}")
