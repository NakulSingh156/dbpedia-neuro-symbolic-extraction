# Occurrence count — how often do Phase-1 abstracts mention an entity without naming it? (2026-10-16)

Roadmap Phase 2.4. Corpus: the 2,000 Phase-1 abstracts, rebuilt in order from the local store with the canonical splitter (`build_sample.py` → `all_sentences.jsonl`, 5,158 sentences; the run had 5,157).

**Status: first pass by Claude (an LLM), not yet checked by a human.** No number below is citable until Nakul's blind 50 gives Cohen's κ (`blind_50_for_nakul.csv` → `kappa.py`).

## Method

1. **Stage 1 — random sample.** 300 sentences (seed 7), every unnamed reference labelled per `GUIDELINES.md` v1.1 (`make_labels.py` → `labels_sample_300.json`, `rates.py` → `results/stage1_rates.json`). Wilson 95% CIs.
2. **Stage 2 — whole-corpus scan.** A high-recall pattern for relational nouns (`his wife`, `X's father`, `the founder of …`) over all 5,158 sentences (`scan.py`), every hit read by hand (`scan_verified.py` → `results/scan_verified.json`, `results/occurrence_summary.json`).

## Results

| Stage 1 (n = 300 sentences) | Sentences | Rate | 95% CI |
|---|---|---|---|
| Any unnamed reference | 130 | 43.3% | 37.9–49.0% |
| …to the **topic** (pronoun / "the film" / implicit) | 120 | 40.0% | 34.6–45.6% |
| …to **another entity** | 18 | 6.0% | 3.8–9.3% |
| O-REL: another entity via a relation ("his brother") | 8 | 2.7% | 1.4–5.2% |
| O-REL whose referent likely has its own KB entry | 3 | 1.0% | 0.3–2.9% |
| O-DESC: another entity, no anchor ("the war") | 9 | 3.0% | 1.6–5.6% |

| Stage 2 (all 5,158 sentences, explicit relational nouns only) | Sentences | Rate | 95% CI |
|---|---|---|---|
| Scan hits | 165 | — | precision 14.5% |
| Genuine O-REL | 24 | 0.47% | 0.31–0.69% |
| …not named anywhere in the abstract | 21 | 0.41% | 0.27–0.62% |
| …and referent likely in a KB | 9 | 0.17% | 0.09–0.33% |

The scan caught 2 of 8 stage-1 O-REL sentences (2 of 3 KB-likely ones), so it is a **lower bound**. It misses plural groups ("eight children"), implicit topic anchors ("The third season"), bridging ("The English adaptation") and "his cabinet".

## What it means

- **Unnamed references are everywhere, but they are almost all the topic.** That is coreference to the abstract's own entity, which coref tiers 1–3 already handle. It is not the paper's problem.
- **The paper's core case — another entity picked out by a relation — is rare in DBpedia abstracts.** About 1 sentence in 40 (stage 1), and about 1 in 600 for an explicit, KB-groundable, never-named relational description (stage 2).
- **It clusters in biographies (kinship) and in nested descriptions** ("the grandson of the founder of Mérida", "a granddaughter of the fourth head of Yonezawa").
- At DBpedia scale (~11.3M abstract sentences) even 0.17% is ~20k sentences, and 2.7% is ~300k. The phenomenon is real but sparse.
- **Consequences:**
  - A random sample cannot build the test set. It must be mined (scan + hand check) and stratified.
  - DBpedia abstracts alone are a thin source. Full Wikipedia article bodies, or biography-heavy text, should be denser — to measure.
  - Agrees with the benchmark survey: 0/120 relational descriptions in Text2KGBench samples.

## Open

- κ from Nakul's blind 50. That set has only 2 O-REL items, so O-REL agreement there is anecdotal; a targeted O-REL check on the 24 scan sentences is the follow-up.
- Density in full article bodies (not just abstracts) — one quick sample would settle whether the source should change.
