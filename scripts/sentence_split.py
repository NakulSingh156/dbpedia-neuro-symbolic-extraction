#!/usr/bin/env python3
"""
CANONICAL sentence splitter for DBpedia abstracts.

Single source of truth on purpose. This logic previously existed as an inline
copy in the Phase-1 runner and as ad-hoc code behind the scaling proposal's
workload estimate. When the glued-boundary bug was found in one, the other kept
the old behaviour and the two numbers silently disagreed. Both now import here.
"""
import re

ABBR = (r"(?:Dr|Mr|Mrs|Ms|St|Jr|Sr|Prof|Rev|Gen|Col|Capt|Lt|Sgt|Inc|Ltd|Co|Corp"
        r"|No|vs|etc|e\.g|i\.e|Mt|Ft|Ave|approx|Fig|Vol|pp)")


def split_sentences(t, min_len=15):
    """Abbreviation-aware split that also repairs missing post-period spaces.

    DBpedia abstracts routinely lose the space after a full stop when wiki
    markup is stripped ("...between 1944 and 1969.He was born in Copenhagen").
    A whitespace-requiring boundary rule leaves those as one blob: 11% of pilot
    sentences, carrying 18% of all triples, averaging 36 words against 22
    overall. Overlong blobs are where the extractor commits to a single fact and
    drops the rest, and where subjects and objects get crossed between clauses.

    The three protective substitutions run BEFORE the repair, so `St.John`,
    `U.S.Government`, `1.5` and `dbpedia.org` are already masked and cannot be
    split by mistake — only a lowercase letter, digit or closing bracket
    followed by a capital qualifies."""
    s = re.sub(rf"\b{ABBR}\.", lambda m: m.group(0).replace(".", "<D>"), t)
    s = re.sub(r"\b([A-Z])\.", r"\1<D>", s)
    s = re.sub(r"(\d)\.(\d)", r"\1<D>\2", s)
    s = re.sub(r'(?<=[a-z0-9)\]"])\.(?=[A-Z])', ". ", s)     # repair glued boundary
    parts = re.split(r"(?<=[.!?])[\"')\]]*\s+(?=[A-Z\"'(\[])", s)
    return [p.replace("<D>", ".").strip() for p in parts
            if len(p.replace("<D>", ".").strip()) > min_len]
