# CHANGES — local index + fix rounds (2026-08-02 → 2026-08-03)

All numbers measured on this Mac (gpt-5.6-luna unless stated). Single-run
noise floor: **±0.03 F1** (measured: an unchanged-code api-arm rerun moved
+0.028 with zero fix events firing).

## Modified files

| file | change |
|---|---|
| `autonomous_pipeline_v13.py` | Node 2 local-index path behind `USE_LOCAL_INDEX` (web path byte-identical); comma-compound canonicalization at emission; inversion gate (inverted-exact ASK + Tier 1.6 range-membership); value-shape exemption + unit/float formatting in `_normalize_literal`; per-sentence retrieved few-shot examples in Node 1. |
| `surface_index.py` | `lookup()`/`candidates()` with tier-dominant ranking; exact-before-stripped normalization; internal punctuation/hyphen fallback variants. |
| `text2kg_harness.py` | + `learn_value_formats()` (train-learned unit/float conventions); + `retrieve_examples()` (BM25+MMR few-shot retrieval, per-domain cached). |
| `chunked_runner.py` | passes `value_formats` and per-sentence `fewshot_examples` into `extract_all_triples`. |
| `export_index.py` / `import_index.py` | v2 dump format: sf:* + rd:* namespaces, count-verified. |
| new: `build_index.py`, `build_popularity.py`, `rescore_index.py`, `repair_tiers.py`, `download_dumps.py`, `eval_ranking.py`, `test_index.py`, `README_INDEX.md`, `RUNBOOK.md` | index build/eval tooling (see README_INDEX.md). |

## Shipped fixes, with measurements

| fix | measured effect | validation |
|---|---|---|
| Local surface-form index (Node 2) | 4_building A/B: api 0.4501 → index 0.4868 (+0.037); second A/B same-day delta +0.057 | benchmark recall@15 97.4%, rank@1 97.4% (4 domains); web path untouched (git-diff verified) |
| Popularity prior + tier-dominant ranking | rank@1 69.2% → 97.4% on gold mentions | sort-key ablation: tier-first 97.4% vs merged 95.1% vs blended 94.6% vs popularity-only 93.4% |
| Tier repair (max-tier-wins) | +3.8 rank@1 (corrupted tiers from HSETNX + trial-run interaction) | Australia case verified; idempotent |
| Exact-before-stripped lookup | benchmark 94.7% → 96.7% recall | "Populous (company)" class |
| Punctuation/hyphen variants | test_3 "108 St. Georges Terrace" 0.00 → 0.67 F1 | fallback-only; 4-domain benchmark unchanged at 97.4% |
| Comma-compound canonicalization (`CANONICALIZE_COMMA_COMPOUNDS`) | 2 gains / 0 breaks on arm-B emissions | blanket version REJECTED: 4 gains / 26 breaks (gold itself holds redirect-form names) |
| Inversion gate (inverted-exact + Tier 1.6) | fired 8× in fresh index arm; contributes to 0.4868 → 0.5352 | unit-tested both directions; network-fail can never trigger a swap |
| Literal formatter (value-shape exemption + learned units) | celestialbody: 40/169 value triples were wrongly always-quoted | 19-domain offline: **69 fixes / 5 breaks** (all 5 = gold's own unit inconsistency), value-format accuracy 37.6% → 44.9% |
| Per-sentence few-shot retrieval (BM25+MMR λ=0.5, NEF §4.3 config) | see 3-domain validation table in final report | train split only; zero extra LLM calls; fixed FORMAT examples retained |

## Rejected / negative results (paper honesty section)

1. **Blanket redirect canonicalization** — 0 fixes / 50 breaks on gold strings;
   4 / 26 on live emissions. Benchmark gold is frozen on an older DBpedia's
   canonical set (e.g. gold `250_Delaware_Avenue`, now a redirect).
2. **Predicate alias widening** — the dominant confusion `location↔country` is
   bidirectional (6 vs 5 in one arm); `architect→significantBuilding` is
   direction-conditional; conditional country-object remap = 6 fixes / 5
   breaks on the index arm at 5.4× train dominance (< 10× bar). Not shipped.
3. **Kotte-class inversions are uncatchable** — (Sri_Lanka, capital, Kotte)
   is absent from DBpedia in both directions and Kotte is typed
   `AdministrativeRegion`, never `City`; neither gate signal can fire.
4. **`_(comicsCharacter)` URIs never existed in DBpedia** (verified in dumps,
   live SPARQL, live Lookup API) — WebNLG annotation artifact. No index
   version fixes comics; only train-example retrieval can teach it.
5. **2-of-3 self-consistency on Node 1** — not built (3× inference cost
   contradicts the cost thesis); final numbers use repeated runs instead.
6. **celestialbody "entity ceiling" was an eval artifact** — zero asteroid-name
   misses; 75.8% of its gold triples are value-typed (formatting, not linking).
7. **monument rank gap** — a single case-twin entity pair
   (`…Infantry_Monument` vs `…_monument`); fix deferred (low yield).

## Known environment quirks

- `USE_TF=0` required where a broken TensorFlow coexists with transformers
  (C-level abseil deadlock on lazy TF import).
- dbpedia.org SPARQL is the main latency source and rate-limits under
  sustained load (100–200 s/sent at worst); the chunked runner's cooldowns
  mitigate.
- dbpedia.owl snapshot affects predicate linking, the literal short-circuit,
  and Tier 1.6 ranges — see RUNBOOK §7.
