# Generic architecture — DBpedia-assumption audit (Phase 5, step 1) — 2026-10-16

Read-only audit of NEF 2.0 (`src/`, frozen at `v14-final`) and the Phase-1 scripts: every place that assumes DBpedia, grouped by the adapter interface that will own it (`METHODOLOGY.md` §3.4). Line numbers are for `src/autonomous_pipeline_v13.py` at HEAD unless a file is named. **Nothing in `src/` is changed by this work.** The generic package lives here in `research/anonymous_nodes/generic/` and wraps or re-implements; the DBpedia adapter must reproduce v14 within ±0.02 (gate G5) before it replaces anything.

Counts (grep, 16 Oct): `dbpedia.org` 31 · `dbo:` 9 · `dbr:` 9 · `_local_name` 8 · `dbpedia.owl` 14 · `DBPEDIA_*` 12 · Redis `sf:`/`rd:`/`pop:` 14 · `normalize_triple` 4.

## OntologyAdapter (schema: properties, domain/range, labels, conventions)

| Where | What it assumes | Generic replacement |
|---|---|---|
| 277–380 `find_ontology`, `load_full_dbpedia_ontology` | `dbpedia.owl` file; keeps only `dbpedia.org/ontology` URIs (326) | `OntologyAdapter.properties()` from OWL/RDFS **or** Wikidata property entities (labels, aliases, P2302 constraints) |
| 127, 566–571, 1217, 2004–2008, 2097 | predicate whitelist = "exists in dbpedia.owl"; `ONTOLOGY_RULES` keyed `dbo:` | `OntologyAdapter.is_property()`, `domain_range()` |
| 1222, 1244 | predicate URI built as `http://dbpedia.org/ontology/{name}` | `OntologyAdapter.property_iri(local)` |
| 1626–1638 | range check by ASK `a dbo:{Type}` | `KBQuery.types()` + `OntologyAdapter.class_hierarchy()` (WD: P31/P279*) |
| 1835–1938 (Judge prompt) | few-shot examples with literal `dbr:`/`dbo:` URIs | prompt templates filled from the adapter (example IRIs per KB) |
| `scripts/predicate_filter.py` | 2,695 `dbo:` properties cached in `data/valid_dbo_properties.json` | adapter-provided property list |
| `scripts/coref_abstract.py` | `dbo:Person` ASK, `rdfs:label`, `foaf:gender` | `KBQuery.types()`, `labels()`, `OntologyAdapter.constraint_filter("gender")` |

## EntityIndex (mention → candidate IDs, popularity)

| Where | What it assumes | Generic replacement |
|---|---|---|
| 151–164, 1120–1177; `src/surface_index.py`; `src/repair_tiers.py` | Redis keys `sf:` (surface forms → `tier|final` DBpedia local names), `rd:` (redirects), `pop:` (in-degree) | `EntityIndex.lookup(mention, k)`, `popularity(id)`; one index per KB (WD: labels + aliases + sitelinks) |
| 148, 1094 | DBpedia Lookup API as the remote fallback | per-KB fallback (WD: `wbsearchentities`) |
| 1138, 1177, 1359, 2684 | resource IRI built as `http://dbpedia.org/resource/{local}` | `EntityIndex.iri(local_id)` |
| 2630–2748 | redirect canonicalisation via `rd:` and a SPARQL check | WD needs none (QIDs are stable); keep in the DBpedia adapter only |
| 2658 `_local_name`; `surface_index.py` | local name = text after the last `/` | adapter-provided `local_id(iri)` |

## KBQuery (facts, existence, neighbourhood)

| Where | What it assumes | Generic replacement |
|---|---|---|
| 147 `DBPEDIA_SPARQL_ENDPOINT`; used at 464, 494, 604, 1576, 1598, 1683, 2685 | one SPARQL endpoint over GET; DBpedia graph | `KBQuery` per KB (WD: QLever primary, WDQS fallback; POST; cached) |
| 451–452 | only `dbpedia.org/resource` IRIs are entities | `EntityIndex.is_entity(iri)` |
| 489–490 | topology via `dbo:wikiPageWikiLink` (DBpedia-only) | `KBQuery.neighbours()`; WD has no wiki-link graph → use statement graph |
| 1576–1683 (SPARQL gate) | fact verification with `dbo:` predicates and DBpedia literals | `KBQuery.has_fact(s, p, o)` with convention-aware comparison (M5) |

## OutputWriter / harness

| Where | What it assumes | Generic replacement |
|---|---|---|
| `src/text2kg_harness.py` `normalize_triple` | output = DBpedia local names (Text2KGBench format) | `OutputWriter` per target: benchmark format, RDF (skolem IRIs + provenance), Wikidata somevalue |
| `scripts/run_phase1_abstracts.py` | `DBPEDIA` env and DBpedia URIs in logs | adapter-agnostic run config |

## What Wikidata needs that DBpedia never did

- **Qualifiers** (P1545 series ordinal, P580/P582 start/end time) → `p:/ps:/pq:` paths for "eldest son", "first club".
- **Schema-uniqueness** from property constraints (P2302: Q19474404 single-value, Q52060874 single-best-value) → grounding tier.
- **Unknown values** (`/.well-known/genid/` skolem IRIs) → count separately, never as answers.
- **Labels in other languages only** (秋月種美 has no English label) → label fallback by language.
- **Popularity** = sitelink count (`wikibase:sitelinks`).
- **Query shape:** transitive paths only from a bound subject (VALUES on both ends times out on QLever).

## Build order (this folder)

1. `ir.py` — the Description IR (done 16 Oct).
2. `relation_lexicon.json` — relational nouns → property paths per KB + constraints (done 16 Oct, v0).
3. `kb_wikidata.py` — Wikidata `KBQuery` with cache, fact masking for simulated MISSING items (done 16 Oct; tests in `tests/`, live ones with `NEF_LIVE=1`: 4/4 pass).
3b. `../testset/make_controlled_prototype.py` — controlled-set generator prototype (done 16 Oct; 434 items from 60 random people).
4. `kb_dbpedia.py` — local oxigraph KBQuery, same interface, capabilities declared (no gender, no redirects, no unknown values; schema-unique never) (done 16 Oct; live test passes). The v14 regression (G5) belongs to the NEF refactor, which has not started.
4b. `detect.py` (M1 prompt + lexicon + `keep()` filter), `eval_detect.py`, `pipeline_dev.py` (M1→M2→M4/M5→M6 on Wikidata) (done 16 Oct, dev results in `results_*_dev_*.json`).
4c. `../testset/sample_cells.py` — per-cell sampler (done 16 Oct): 560 items, 79/90 cells full.
5. `decide.py` (M5–M6), `writer.py` (M7) — after Tsoru's representation decision.
