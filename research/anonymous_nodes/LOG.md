# Working log — anonymous-node grounding paper

One entry per working block. Newest first.

## 2026-10-17 (early) — next build round
- **Controlled set, end to end (Llama, templates, 575 items):** first pass 503/575 (87.5%), 0 wrong identities; all 72 errors = NOT-DETECTED, all in the possessive form. Cause: the detector normalises "Peter Egeli's father" → "his father" and the filter required the literal mention. Fix in `keep()`: accept when the relation noun occurs in the sentence. → **575/575, 0 wrong identities**; dev set unchanged (20/23 paths, 1/60 false alarms). **This is a plumbing check, not a result:** gold and pipeline share the lexicon paths, and template sentences are easy. Real tests: paraphrased sentences, nested descriptions, the natural set.
- Realiser bug: used the relation's gender for the anchor ("Margaret … a biography of him") → anchor gender now from P21. Paraphrased variant + its evaluation running.
- Tsoru doc: §9 "Prototype status" added (5 pages); G1 row refreshed.
- **Sampler** pools 60 → 250: 575 items (425 real + 150 simulated), **84/90 cells full**; only father/mother ambiguous short (structural; the few found are single-best-value violations).
- **Surface realisation** (`testset/realise.py`): template texts for all 575 (true intro from the anchor's Wikidata description + neutral sentence; possessive / of-phrase / pronoun); disambiguators stripped from names; LLM paraphrase ready, not yet run.
- **Comparator M5** (`generic/compare.py`, `wikidata/eval_compare.py` on the 60 coded pairs): v1 (containment/subclass/nationality/sport links) merged C 5/30, K 0/8. Cause: **23/60 text-side QIDs are disambiguation pages** ("American" Q463180, "Italian", "Rock"; "Electronic" → an album). v2 adds demonym-on-label (P1549), demonym→country→containment (restricted to country/state/constituent/historical-country types), occupation→direct sport/field→subclass, same-label: **C 20/30 merged, K 1/8 (Russian vs France), X 2/19 (English vs UK)**. M2 rule to add: never link to disambiguation pages.
- **Containment bug:** transitive P361 climbs into alliances and back (Russia → … → France). New strict closure: P361/P749 only as the first hop, then P131/P17/P706/P276. **Re-check of the 16 Oct granularity merges: WD 157/161 kept, DBP 25/25** (dropped: Lubin/Gmina Strzelin vs Germany, New Spain vs Mexico, an Italian region) → agreement ≈ 96.2% (was 96.3%); the Tsoru-doc figure stands.
- Strict closure still leaks through alliance items that list members under P17: among the 157 strict merges, 4 join two sovereign states — 2 false (Azerbaijan/Armenia, Italy/France), 2 fine (Kingdom of Denmark/Denmark). Clean WD granularity 155/161 → agreement still ≈ 96.2%. Rule added: two different sovereign states are never variants (slightly over-strict on Kingdom of Denmark/Denmark).
- **Disambiguation fix (M2):** `WikidataKB.qid_for_title` rejects disambiguation pages (pageprops + P31 Q4167410); `Comparator` compares a disambiguation item by label only. Live test added (6/6 pass).

## 2026-10-16 (late night) — build steps 1–3
- **Per-cell sampler** (`testset/sample_cells.py`): global sitelink quantiles for 2,154,452 humans with enwiki (P33=2, P50=3, P90=12, P95=18, P99=38) → tiers tail ≤2 / mid 3–17 / head ≥18. Reproducible MD5-seeded anchor pools. 10 nouns × 3 tiers × 3 types, quota 5 → **560 items (410 real + 150 simulated-missing), 79/90 cells full**; father/mother ambiguous ≈ impossible (schema-unique); a few spouse/sister ambiguous cells short (pool 60).
- **QLever gotcha:** numeric FILTER on `wikibase:sitelinks` (xsd:int) silently returns nothing; cast with `xsd:integer(?n)`. First sampler run filled 0/90 cells because of it → empty pools now raise. Checked: the Wikidata survey's `FILTER(?n > 1)` is on a COUNT (xsd:integer) and worked (containment checked 200/relation).
- **DBpedia KBQuery** (`generic/kb_dbpedia.py`): local store has no foaf:gender → gender filter declared unsupported; Marie Antoinette has 1 spouse in DBpedia vs 2 in Wikidata. Tests 5/5 (live).
- **M1 detector** (`generic/detect.py`) + dev eval + end-to-end dev pipeline: see METHODOLOGY finding 16. Llama 20/23 paths, filter cuts false alarms 59/60 → 1/60; end to end 20/23 = oracle, 0 wrong identities.

## 2026-10-16 (night) — building started (decision-independent pieces)
- `generic/ARCHITECTURE.md`: DBpedia-assumption audit of `src/` + scripts, grouped by adapter interface (OntologyAdapter / EntityIndex / KBQuery / OutputWriter), plus what Wikidata needs that DBpedia never did.
- `generic/ir.py` (Description IR, nested anchors, hops with alternative properties), `generic/relation_lexicon.json` v0 (44 relational nouns → WD + DBpedia paths + gender), `generic/lexicon.py` (chain expansion, plural/synonym folding).
- `generic/kb_wikidata.py`: QLever→WDQS, POST, disk cache, KBUnavailable on failure (never empty), bound-subject paths, lenient gender filter, unknown-value count, ancestors, single-value-constraint lookup, schema_unique(), labels with language fallback, sitelinks, fact masking. Tests: 3 offline + 1 live, all pass (Marie Antoinette 2 spouses; Uesugi father 秋月種美; father schema-unique, spouse not).
- `testset/make_controlled_prototype.py`: 60 random enwiki humans → 434 items. Wikidata has none of the asked kin in 96% of slots → per-cell sampling needed; global popularity quantiles.

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
