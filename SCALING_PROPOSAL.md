# NEF 2.0 at Scale — Extracting RDF from Wikipedia Abstracts

**A resource, cost, and time study for DBpedia** · Nakul Singh, GSoC 2026 · mentors: Ara, Tommaso Soru
*Status: draft for mentor review. Every number below is either measured from our
benchmark runs, counted from our loaded DBpedia snapshot (query shown), or
carries a dated external source.*

## 1. What we're proposing

Run the NEF 2.0 pipeline (this repository; Docker image
`ghcr.io/nakulsingh156/dbpedia-extractor:v14`) over English Wikipedia abstracts
to produce a new, provenance-tagged RDF dataset for the DBpedia Databus —
**triples only on the Databus, the stack stays in the Docker image**, per
Tsoru's guidance. Phased rollout with review gates, starting with a
mentor-reviewed example batch, so DBpedia commits resources only after seeing
output quality at each step.

## 2. Why this is worth DBpedia's sponsorship

1. **Abstracts contain facts infoboxes don't.** DBpedia's mapped triples come
   overwhelmingly from infoboxes; the prose abstract of an article routinely
   asserts relations that never appear in any infobox field. This pipeline
   reads the prose.
2. **Every triple carries a trust tag.** The verification gate labels each
   output `verified` (already supported by DBpedia) or `faithful-unverified`
   (asserted by the sentence, absent from DBpedia — i.e. **the new knowledge**).
   Reviewers and downstream users can filter by trust level; the unverified
   slice *is the product*.
3. **Benchmark-validated quality.** Macro F1 0.6317 on Text2KGBench
   dbpedia_webnlg — parity with the GPT-4o NEF 1.0 baseline (0.628) at 3–4×
   lower end-to-end cost ([REPORT.md](REPORT.md)).
4. **Fully open, reproducible stack.** Local surface-form index + local SPARQL
   store, both built from Databus artifacts; the only external call is an
   OpenAI-compatible LLM endpoint — swappable for a self-hosted open model.

## 3. The workload, measured (not estimated)

Counted directly from our loaded snapshot (oxigraph, `short_abstracts_en.ttl`,
load 2026-06-27):

```sparql
SELECT (COUNT(*) AS ?c) WHERE { ?s rdfs:comment ?o }        # → 4,643,098
```

Sentence statistics from a 400-abstract sample (`STRLEN > 40` filter to skip
parse-artifact literals; sentence split on terminal punctuation):

| Quantity | Value | Source |
|---|---|---|
| English short abstracts | **4,643,098** | count query above, our snapshot |
| Sentences per abstract | **2.26 mean / 2 median** | 400-abstract sample |
| Words per abstract | 44.8 mean | same sample |
| **Total sentences (full corpus)** | **≈ 10.5 M** | 4.64 M × 2.26 |

*Scope note:* these are **short** abstracts (lead paragraph). Long abstracts
(`long_abstracts_en.ttl`) run ~2–3× more sentences; everything below scales
linearly if DBpedia prefers that target.

## 4. Cost model

**Measured unit cost** (2,014-sentence benchmark + 602-sentence rerun, GPT-5.6
Luna via OpenRouter at $0.10/$0.60 per M tokens, 8–12 calls/sentence):
**≈ $0.004–0.005 per sentence**. [Exact OpenRouter invoice total to be attached
from the account's Activity page.]

### Option A — API-served model (turnkey)

| Scope | Abstracts | Sentences | LLM cost | Wall-clock @ 50 concurrent |
|---|---|---|---|---|
| **Phase 0 — review batch** | 100 | ~226 | **< $2** | ~ 1 hour |
| **Phase 1 — pilot** | 100 k | ~226 k | **≈ $0.9–1.1 k** | ~ 1.5 days |
| **Phase 2** | 1 M | ~2.26 M | ≈ $9–11 k | ~ 2 weeks |
| **Phase 3 — full corpus** | 4.64 M | ~10.5 M | **≈ $42–53 k** | ~ 9 weeks |

Throughput math: measured ~27 s/sentence end-to-end is LLM-latency-bound (the
local index and store answer in milliseconds), so it parallelises to ~C/27
sentences/s at concurrency C. C = 50 → ≈ 160 k sentences/day per orchestrator;
scales linearly with workers/API limits. Infrastructure beyond the LLM: the
current 8 GB VPS already hosts index + store + pipeline (≈ €10–15/month class).

### Option B — self-hosted open model (cheaper at scale, needs a quality pilot)

The endpoint is OpenAI-compatible; a vLLM-served open model on one rented GPU
(A100/H100 class, ~$1.5–3/hr on Runpod/Lambda-class pricing) turns cost from
per-token to per-hour. At realistic batched-serving throughput this lands the
**full corpus in the low-thousands of dollars** — but output quality with an
open model on the v14 pipeline is unmeasured (our LLaMA-3.3-70B number, 0.4387,
predates the index/gate/fixes). **Phase 1 should include a benchmark re-run of
one open model (~$0 API cost if self-hosted) before committing Option B.**

### Model-scaling ablation (recommended, one-time, ≈ $50)

Same pipeline, GPT-4o, 5-domain benchmark subset — isolates pipeline-vs-model
contribution and tells DBpedia what quality ceiling to expect if it ever wants
to pay for a premium model. Strengthens any publication as well.

## 5. Quality control plan

- **Gate provenance**: every triple tagged `verified` / `faithful-unverified`;
  publishable as a quality annotation in the dataset.
- **Sampled precision audit per phase**: N = 200 random triples manually
  reviewed (mentors + contributor) before the next phase unlocks; publish the
  audited precision with the dataset.
- **Open-domain caveat, stated honestly**: benchmark F1 was measured with
  per-domain ontology bounding; production runs rank over the full DBpedia
  ontology (already supported). Phase 0/1 exist precisely to measure quality in
  the open-domain setting before real money is spent.

## 6. Output and publication

- Expected yield ≈ 2–3 extracted triples/sentence → **≈ 20–30 M triples** for
  the full corpus, ≈ 3–5 GB as N-Triples.
- Published to the **DBpedia Databus as a versioned dataset (triples only)**,
  with per-triple provenance (source sentence ID + verification status);
  regenerable per Wikipedia/DBpedia release cycle.
- The stack remains distributed as the Docker image (GHCR), reproducible from
  this repository + Databus source artifacts.

## 7. Phased plan with decision gates

| Phase | Deliverable | Cost | Gate to proceed |
|---|---|---|---|
| 0 | 100 abstracts through the deployed stack; traced outputs shared for mentor review | < $2 | mentors judge output quality |
| 1 | 100 k abstracts + 200-triple precision audit + open-model benchmark re-run | ≈ $1 k | audited precision acceptable; Option A vs B decision |
| 2 | 1 M abstracts, first Databus release (beta) | ≈ $10 k | community/DBpedia review of beta dataset |
| 3 | Full corpus + versioned Databus release | ≈ $45–55 k (A) or ~10× less (B) | — |

**The ask to DBpedia**: sponsor Phase 1 (≈ $1 k + review time). Phases 2–3 only
on the strength of Phase 1's audited numbers.

## 8. Risks, honestly

| Risk | Mitigation |
|---|---|
| Open-domain quality below benchmark quality | Phase 0/1 measure it before scale; precision audits gate every phase |
| API provider variance / rate limits | measured at macro ±0.005 on the benchmark; self-hosted Option B removes it entirely |
| Cost estimate drift | unit cost is measured, not modeled; invoices attached per phase |
| Abstract parsing artifacts (junk literals observed in snapshot) | length/character filters (already applied in our sampling); counted into yield estimates |

## Appendix A — traced examples

*To be filled from the Phase-0 batch: 3 full traces (sentence → candidates →
ranking → judge → gate tier → emitted triples with status), produced by the
deployed container.*

## Appendix B — sources

- Workload counts/samples: SPARQL queries in §3 against our snapshot (load
  manifest in [REPRODUCIBILITY.md](REPRODUCIBILITY.md)).
- Unit cost: measured benchmark spend (OpenRouter pricing page, 2026-08;
  invoice to be attached).
- Benchmark result and variance: [REPORT.md](REPORT.md), tag `final-results-0.6317`.
- NEF 1.0 baseline cost: mentor-reported (~$30–35 full benchmark), exact figure
  to be confirmed by mentors.
