# Benchmark survey — step 2 of the roadmap (2026-10-16)

**Question (Tsoru):** which existing benchmarks could evaluate anonymous-node grounding, which ontology do they use, and do they contain unnamed entities at all?

Full table: [`../benchmark_matrix.csv`](../benchmark_matrix.csv).

## What was measured (both Text2KGBench halves, local copy)

Proxy: an entity-valued gold subject/object counts as "unnamed" if its name is not in the sentence (no full match, < 50% of content tokens). 60 random hits per dataset were labelled by hand (`results/*_unnamed_sample_labelled.json`).

| | Wikidata-TekGen | DBpedia-WebNLG |
|---|---|---|
| Raw proxy rate (entity mentions) | 10.38% | 2.48% |
| Proxy precision (hand-checked, 60 hits) | 98.3% | 5.0% |
| **Estimated unnamed mentions** | **≈ 10.2%** | **≈ 0.1%** |
| Test sentences with ≥ 1 unnamed entity (raw) | 17.7% | 10.0% (mostly aliases) |
| Topic as definite description ("The film …") | 37 / 60 | 0 |
| Topic not referenced (truncated / implicit) | 20 / 60 | 0 |
| Partial name | 1 / 60 | 3 / 60 |
| Alias / literal false positive | 1 / 60 | 57 / 60 |
| **Description of a different entity ("X's husband")** | **0 / 60** | **0 / 60** |

## Findings

1. **Unnamed entities are common in real text but absent from WebNLG-derived data.** WebNLG sentences are written from triples, so every entity is named. Systems tuned on it never see the phenomenon.
2. **TekGen's unnamed entities are almost all the article's own topic** — "The film was made by …" in the article about that film. Resolving them needs document context, which sentence-level evaluation never provides. One TekGen sentence ("The film was made by Wien-Film …") is gold-labelled for six different films: unresolvable in principle from the sentence.
3. **The paper's core case — a relational description of another entity — appears in neither benchmark** (0/120 hand-labelled hits). That justifies building our own test set.
4. **Our task combines four existing tasks**, each with its own benchmark covering only that piece: detection (bridging anaphora: ISNotes, BASHI, ARRAU), formalisation (KBQA: QALD-10, LC-QuAD 2.0), grounding with abstention (EL with NIL: AIDA-CoNLL), and KG extraction (Text2KGBench). No benchmark covers the combination.
5. **LC-QuAD 2.0 can seed the test set**: it gives SPARQL for both Wikidata and DBpedia, so its one-hop questions ("What is the spouse of X?") become descriptions ("X's spouse") with gold answers on both KBs.
6. Two unnamed-entity types should be kept separate in the paper:
   - **Topic-coreferent** ("The film …") — resolved from document context (our coref tier 3); TekGen evaluates it.
   - **Relational** ("Marie Antoinette's husband") — resolved by a KB query; nothing evaluates it yet.

Note: Text2KGBench is co-authored by Nandana Mihindukulasooriya (one of our mentors).

## Still to verify
CoNLL-2012 size/licence/mention types; QALD-10 size; licences marked "check"; REBEL and DocRED unnamed rates (expected low, not measured). And ask Tsoru which CoNLL and Wikidata benchmarks he meant.
