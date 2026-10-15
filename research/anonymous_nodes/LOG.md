# Working log — anonymous-node grounding paper

One entry per working block. Newest first.

## 2026-10-16
- Started roadmap steps 1–3 (Part III, Phase 1 + 2 of PROJECT_CONTEXT.md).
- Wikidata survey (`wikidata/survey_wikidata.py`): population uniqueness on Wikidata items with an English Wikipedia article (exact, via QLever) + paired per-fact comparison against DBpedia on Phase 1 facts.
- Found during smoke tests: Wikidata stores "unknown value" as `.well-known/genid` skolem IRIs (native anonymous node); local DBpedia store has no redirect table, so names are mapped to QIDs through the Wikipedia API (redirect-aware); Marie Antoinette has two truthy P26 values in Wikidata (Louis XVI and Axel von Fersen the Younger).
- Benchmark survey and related-work pass 1 begun.
