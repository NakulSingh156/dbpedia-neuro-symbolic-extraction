# Working log — anonymous-node grounding paper

One entry per working block. Newest first.

## 2026-10-16 (later)
- Occurrence count (Phase 2.4), see `occurrence/README.md`. First pass by Claude; awaiting Nakul's blind 50 for κ.
- Stage 1, 300 random sentences: 43% hold an unnamed reference, but 40% are the topic itself. Another entity: 6.0%. Relational (O-REL): 2.7% (CI 1.4–5.2%). KB-likely O-REL: 1.0%.
- Stage 2, scan of all 5,158 sentences: 24 genuine O-REL sentences (0.47%); 9 KB-likely and never named (0.17%). Scan recall on stage 1 is 2/8, so it is a lower bound.
- Guidelines v1.1: `kb_entity` flag added; T-ZERO and exclusions clarified after batch 1.
- Correctness-decomposition background job failed (QLever gave up after 7 retries). To rerun.

## 2026-10-16
- Started roadmap steps 1–3 (Part III, Phase 1 + 2 of PROJECT_CONTEXT.md).
- Wikidata survey (`wikidata/survey_wikidata.py`): population uniqueness on Wikidata items with an English Wikipedia article (exact, via QLever) + paired per-fact comparison against DBpedia on Phase 1 facts.
- Found during smoke tests: Wikidata stores "unknown value" as `.well-known/genid` skolem IRIs (native anonymous node); local DBpedia store has no redirect table, so names are mapped to QIDs through the Wikipedia API (redirect-aware); Marie Antoinette has two truthy P26 values in Wikidata (Louis XVI and Axel von Fersen the Younger).
- Benchmark survey and related-work pass 1 begun.
