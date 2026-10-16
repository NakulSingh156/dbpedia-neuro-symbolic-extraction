# Working log — anonymous-node grounding paper

One entry per working block. Newest first.

## 2026-10-16 (evening) — three pre-meeting probes
- **Related work pass 2b** (`related_work.md`): GrailQAbility (read in full core), RetinaQA, Hou 2020, EDC, Learn to Not Link. Gap holds: KBQA answerability has our MISSING (≈NA) and UNRESOLVED (≈NK) but no AMBIGUOUS (answers are sets), no extraction, no unnamed-entity representation. Borrowed: deletion-based MISSING items with inverse-popularity sampling; abstention-reason check; discriminative compile-then-decide; "X of what?" anchor questions; define-then-retrieve relation mapping.
- **Extraction mode** (`occurrence/extraction_mode.py`, `extraction_graded.py`): same 23 descriptions, plain "extract triples with canonical names" prompt. Lost or junk: Qwen 17/23 (74%), Llama 16/23 (70%) — PHRASE 10/10, FLATTENED 5/4, DROPPED 2/2; NAMED_OK 5/6; NAMED_WRONG 1/0. → the failure is junk/lost entities, not invented names. Added the junk-node-rate metric.
- **Schema-unique vs data-unique** (`wikidata/schema_uniqueness.py`): Wikidata single(-best)-value constraints on only 5/57 mapped properties (P19, P20, P22, P25, P36). Place relations, exact + containment: 90.1% agreement schema-unique (n=101) vs 78.4% data-unique (n=328). Schema-unique relations unique in 99.0% of covered facts. DBpedia: 31 functional properties, none of our object relations.
- **Density probe** (`occurrence/density_probe.py`, `density_verified.py`): 50 people, all sentences hand-checked among 204 scan hits. Per 100 sentences (non-fiction): abstract 2.9, article lead 1.5, article body 1.6; per person: body 0.50 vs abstract 0.08 (≈6×). Named elsewhere in the text: 25–31%. Wikipedia API rate-limited us (429) → cached extracts, 3 s pacing.
- **Headroom teaser** (`occurrence/headroom_teaser.py`, `headroom_graded.py`): 23 real descriptions, oracle parse. Wikidata: 7 grounded, 15 missing, 1 anchor absent. Qwen2.5-7B / Llama-3.1-8B (UNKNOWN allowed): 0 wrong entities; abstain 16/13; only the KB named William Winter and 秋月種美 (Akizuki Tanemi). Found and fixed two scan labels (Sol Levi's brother is named elsewhere; Pons Santolh's brother-in-law is inferable).
- METHODOLOGY → v1.1 (findings 11–14, M2b in-document resolution, grounding tier, facts-kept headline, decision 8). Word doc rebuilt (5 pages).

## 2026-10-16 (later)
- `METHODOLOGY.md` v1: architecture (Description IR, modules M1–M7, adapter interfaces, output representation), approaches B0–B4 + N/H, RQ→experiment map, two-part test set (controlled + mined natural), metrics, plan, decisions needed from Tsoru.
- Occurrence count (Phase 2.4), see `occurrence/README.md`. First pass by Claude; awaiting Nakul's blind 50 for κ.
- Stage 1, 300 random sentences: 43% hold an unnamed reference, but 40% are the topic itself. Another entity: 6.0%. Relational (O-REL): 2.7% (CI 1.4–5.2%). KB-likely O-REL: 1.0%.
- Stage 2, scan of all 5,158 sentences: 24 genuine O-REL sentences (0.47%); 9 KB-likely and never named (0.17%). Scan recall on stage 1 is 2/8, so it is a lower bound.
- Guidelines v1.1: `kb_entity` flag added; T-ZERO and exclusions clarified after batch 1.
- Correctness decomposition rerun and done (`wikidata/decompose_mismatches.py`). The first attempt silently failed: QLever times out when both ends of a transitive path come from VALUES. Fix: fetch each entity's ancestors once from a bound subject, compare in Python, cache. 0 unchecked.
  - Granularity explains 25/74 DBpedia and 161/465 Wikidata mismatches.
  - Hand coding of the residue (`code_disagreements.py`; 40 WD + 20 DBP): mostly *convention* — demonym vs country, historical polity, author vs writer, player vs sport (WD 21/40, DBP 9/20) — and *our own extraction/link errors* (11/40, 8/20). Real KB-vs-text difference: 5/40 and 3/20.
  - Corrected: when the KB answers, it agrees with the text ~96% (WD) / ~98% (DBP), excluding text errors. **The earlier 57.9% vs 83.8% gap was a modelling-convention artefact, not Wikidata being less accurate.**
- Related-work pass 2: Perera 2016 read in full; Hosseini line (thesis) and OpenEL read for setup and NIL policy. Gap statement survives; implicit EL must be cited as the origin of "reference through characteristics" (`related_work.md`).

## 2026-10-16
- Started roadmap steps 1–3 (Part III, Phase 1 + 2 of PROJECT_CONTEXT.md).
- Wikidata survey (`wikidata/survey_wikidata.py`): population uniqueness on Wikidata items with an English Wikipedia article (exact, via QLever) + paired per-fact comparison against DBpedia on Phase 1 facts.
- Found during smoke tests: Wikidata stores "unknown value" as `.well-known/genid` skolem IRIs (native anonymous node); local DBpedia store has no redirect table, so names are mapped to QIDs through the Wikipedia API (redirect-aware); Marie Antoinette has two truthy P26 values in Wikidata (Louis XVI and Axel von Fersen the Younger).
- Benchmark survey and related-work pass 1 begun.
