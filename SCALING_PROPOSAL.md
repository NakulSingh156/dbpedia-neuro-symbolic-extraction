# NEF 2.0 at Scale — Extracting RDF from Wikipedia Abstracts

**A resource, cost, and time study for DBpedia** · Nakul Singh, GSoC 2026 · mentors: Ara, Tommaso Soru
*Status: revision 2, 2026-08-22 — now carries measured open-domain results (§5) including our own precision audit. Draft for mentor review. Every number below is either measured from our
benchmark runs, counted from our loaded DBpedia snapshot (query shown), or
carries a dated external source.*

## 1. What we're proposing

Run the NEF 2.0 pipeline (this repository; Docker image
`ghcr.io/nakulsingh156/neural-extraction-framework:v2.0`) over English Wikipedia abstracts
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
   dbpedia_webnlg — level with the GPT-4o NEF 1.0 baseline (0.628) at 3–4×
   lower end-to-end cost ([REPORT.md](REPORT.md)). *The method's contribution is now isolated: with base model and index
   held fixed, NEF 2.0 beats NEF 1.0 by +0.018 (0.6317 vs 0.6137), and the two
   base models differ by 0.002 in an identical harness — so the result is not
   the model. See §4.*
4. **Fully open, reproducible stack.** Local surface-form index + local SPARQL
   store, both built from Databus artifacts; the only external call is an
   OpenAI-compatible LLM endpoint — swappable for a self-hosted open model.

## 3. The workload, measured (not estimated)

Counted directly from our loaded snapshot (oxigraph, `short_abstracts_en.ttl`,
load 2026-06-27):

```sparql
SELECT (COUNT(*) AS ?c) WHERE { ?s rdfs:comment ?o }        # → 4,643,098
```

Sentence statistics from a **stratified sample of 5,000 abstracts** — 20 evenly
spaced strata of 250 across the full 4.64 M rows, so the sample is not a single
contiguous block. Sentence splitting protects abbreviations (`Dr.`, `St.`,
`U.S.`), initials (`J. R. R.`) and decimals before splitting on terminal
punctuation; segments under 15 characters are discarded.

| Quantity | Value | Source |
|---|---|---|
| Rows with `rdfs:comment` | **4,643,098** | count query above, our snapshot |
| Parse-artifact rows | **6.46 %** | 323 of 5,000 — 262 too short, 42 list pages, 19 disambiguation |
| Usable abstracts | **≈ 4.34 M** | 4.64 M × 93.5 % |
| Sentences per abstract | **2.61 mean / 2 median** (95 % CI ± 0.037) | 5,000-abstract sample |
| **Total sentences (full corpus)** | **≈ 11.3 M** (± 0.16 M) | 4.34 M × 2.61 |

> **Correction, 2026-08-22.** These replace 5.2 % / 4.40 M / 2.31 / ≈10.2 M in the
> previous draft. Two causes, both now fixed:
>
> 1. **The sentence splitter under-counted.** DBpedia abstracts routinely lose
>    the space after a full stop when wiki markup is stripped
>    (`"...between 1944 and 1969.He was born in Copenhagen"`). The old rule
>    required whitespace at the boundary, so those arrived as one sentence.
>    11 % of pilot sentences were affected, carrying 18 % of all triples, at 36
>    words mean against 22 overall. Sentences/abstract rises 2.31 → 2.61 (+13 %).
> 2. **Artifact criteria are now itemised** rather than length-only, so a
>    reviewer can disagree with any one of them. The length-only figure
>    reproduces at 5.24 %, confirming the old number was correct for what it
>    measured — just narrower.

*Robustness:* computing the total two ways — every row including artifacts
(4.64 M × 2.19) versus usable abstracts only (4.40 M × 2.31) — gives 10.18 M and
10.17 M respectively, so the estimate is not sensitive to how artifacts are
handled. An earlier 400-abstract, naive-split sample gave 10.5 M; the refined
method lands within 3 % of it.

*Scope note:* these are **short** abstracts (lead paragraph). Long abstracts
(`long_abstracts_en.ttl`) run ≈2–3× more sentences; everything below scales
linearly if DBpedia prefers that target.

## 4. Cost model

**Measured unit cost** (2,014-sentence benchmark + 602-sentence rerun, GPT-5.6
Luna via OpenRouter at $0.10/$0.60 per M tokens, 8–12 calls/sentence):
**≈ $0.004–0.005 per sentence**. [Exact OpenRouter invoice total to be attached
from the account's Activity page.]

### Option A — API-served model (turnkey)

| Scope | Abstracts | Sentences | LLM cost | Wall-clock @ 50 concurrent |
|---|---|---|---|---|
| **Phase 0 — review batch** | 100 | ≈231 | **< $2** | ≈ 1 hour |
| **Phase 1 — pilot** | 100 k | ≈231 k | **≈ $0.9–1.2 k** | ≈ 1.5 days |
| **Phase 2** | 1 M | ≈2.31 M | ≈ $9–12 k | ≈ 2 weeks |
| **Phase 3 — full corpus** | 4.40 M | ≈10.2 M | **≈ $41–51 k** | ≈ 9 weeks |

Throughput math: measured ≈27 s/sentence end-to-end is LLM-latency-bound (the
local index and store answer in milliseconds), so it parallelises to ≈C/27
sentences/s at concurrency C. C = 50 → ≈ 160 k sentences/day per orchestrator;
scales linearly with workers/API limits. Infrastructure beyond the LLM: the
current 8 GB VPS already hosts index + store + pipeline (≈ €10–15/month class).

### Option B — self-hosted open model (measured; this is what Phase 1 ran on)

The endpoint is OpenAI-compatible; a vLLM-served open model on one rented GPU
(A100/H100 class, ≈$1.5–3/hr on Runpod/Lambda-class pricing) turns cost from
per-token to per-hour. At realistic batched-serving throughput this lands the
**full corpus in the low-thousands of dollars** — but output quality with an
open model on the v14 pipeline is unmeasured (our LLaMA-3.3-70B number, 0.4387,
predates the index/gate/fixes). **Done: Qwen-2.5-7B scores 0.5490 macro on the full benchmark — 86.9 % of Luna
— at zero API cost, and is the model behind every Phase 1 number in §5.**

### Controlled model experiment — COMPLETED (cost ≈$16, not the $180–200 budgeted)

The headline benchmark comparison changes two variables at once — method
(NEF 1.0 → NEF 2.0) *and* base model (GPT-4o → GPT-5.6 Luna) — so it cannot
separate "the pipeline is better" from "the model is better". Holding the model
fixed resolves it:

| | NEF 1.0 (method) | NEF 2.0 (method) |
|---|---|---|
| **no-method 6-shot baseline** | GPT-4o **0.5474** | Luna **0.5454** |
| **Both approaches on LUNA** | **0.6137** | **0.6317** |

**Resolved — the confound is gone, at ≈$16 rather than the $180–200 budgeted.**
The two base models score within 0.002 of each other in an identical harness
(GPT-4o 0.5474 vs Luna 0.5454), so the model is *not* carrying the result. With
model and index both held fixed, method alone accounts for **+0.018** (NEF 1.0
0.6137 → NEF 2.0 0.6317), improving 10 of 19 domains.

An open-weight model was also measured end-to-end on the same pipeline:
**Qwen-2.5-7B local, macro 0.5490 — 86.9 % of Luna's score at zero API cost.**
This is the evidence behind Option B below, and it is what the Phase 1 run uses.

Running NEF 2.0 on GPT-4o over the full benchmark (≈$180–200, ≈16 h) gives a
clean method-vs-method comparison at a fixed model, and turns the Luna run into
a separate, honest efficiency result rather than a confounded quality claim.
Recommended sequencing: a 3-domain pilot (≈$25) first, since prompts and
thresholds were tuned with Luna in the loop.

This is a benchmark experiment, not part of the abstract-extraction budget, but
it belongs in the same funding conversation.

## 5. Phase 1 — measured on real Wikipedia abstracts

Everything above §4 is benchmark evidence: 19 domains, a fixed list of allowed
predicates per domain, gold triples to score against. **None of that is the
production setting.** Phase 1 removes the scaffolding — open-domain extraction
over abstracts sampled from our snapshot, no allowed-predicate list, ranking
over the full 2,695-property ontology, no gold to score against.

*Run in progress at time of writing: 1,527 of 2,000 abstracts. Figures are
in-flight and stable to within 2 % across the last 1,200 abstracts; final
numbers follow on completion.*

| Quantity | Measured | Note |
|---|---|---|
| Triples per abstract | **5.07** | 7,747 triples from 1,527 abstracts |
| Triples per sentence | **2.30** | |
| Candidate survival | **63 %** | 63 % of proposed triples pass linking, judge and gate |
| Distinct predicates | **995** | top 20 cover only 37 % — a genuine long tail |
| `verified` (already in DBpedia) | 13.9 % of URI-triples | |
| `faithful-unverified` (**new knowledge**) | **2,730** | 1.79 per abstract |
| Literal-valued | 4,556 (59 %) | dates, numbers, names — not URI-linkable |
| **Corpus projection** | **≈22.0 M triples, ≈7.8 M novel URI-triples** | 4.34 M abstracts |

The 995 distinct predicates matter more than the raw count: every benchmark
number in this document, ours and NEF 1.0's, comes from 19 domains with fixed
predicate lists. This is the evidence the pipeline works without them.

### 5.1 Precision — our own audit, before the mentor audit

**Internal estimate: ≈60 % precision** (`faithful AND correctly linked`), from
strict annotation of 50 of a 200-triple random sample. At n = 50 the 95 %
interval is roughly 46–74 %, so read it as "around 60, definitely not 85".


Defects are concentrated and mechanical, not diffuse:

| Class | ≈Share | Example | Fix |
|---|---|---|---|
| Definite-description subject | 9 % | `The_Road \| routeStartLocation \| "FM 1573 in Gruver"` in an abstract about FM 2018 | extend abstract-level coreference to definite descriptions |
| Wrong / nonsense predicate | ~10 % | `countySeat` for a cricketer's county club | tighter domain/range type-gating |
| Reversed direction | ~5 % | `Caltech \| location \| Kenneth_G._Libbrecht` | schema domain/range check at emission |
| Garbled literal | ~5 % | multi-clause text captured as one literal | literal segmentation |
| Wrong entity sense | ~5 % | `Joe_Walsh \| plays \| mandolin` links to the Eagles guitarist | popularity/type disambiguation |

The first two are ~19 % combined and share machinery that already exists — the
same coreference and type-guard code that took pronoun-subject contamination
from 19.8 % to 0 %. **Our own target before claiming ingestion-readiness is
80 %+, and we do not claim it today.**

### 5.2 Throughput — and what the GPU is actually for

Measured on one MacBook Pro CPU with a local Qwen-2.5-7B: **42.5 abstracts/hour**.

```
4,343,153 abstracts ÷ 42.5/hour  =  102,000 hours  =  11.7 years
```

That is the entire ask, stated as arithmetic. We are **not** projecting a GPU
throughput number we have not measured — batched GPU serving behaves differently
from CPU inference, and quoting an unmeasured speedup would be the weakest claim
in this document. What we can say: the quality is measured, the yield is
measured, the CPU throughput is measured, and the gap between 11.7 years and any
usable timeline is what the hardware closes.

### 5.3 Pipeline defects found and fixed during Phase 1

Reported because they bound how much of this document's earlier drafts to trust:

| Defect | Impact | Status |
|---|---|---|
| Cross-sentence pronouns unresolved | 19.8 % of triples had a pronoun subject (`He` linked to *helium*) | fixed — 0 % |
| Sentence splitter missed glued boundaries | 11 % of sentences were two sentences merged | fixed — 0 % |
| Invented URIs on open-domain text | 27.7 % of triples referenced non-existent entities | fixed — 1.9 % via emission-time existence check |
| Non-English / invalid predicates | 3.4 % of triples | fixed — 0 % |

Verified-triple rate rose 8.3 % → 13.9 % as a direct consequence of subjects
becoming real entities.

## 6. Quality control plan

- **Gate provenance**: every triple tagged `verified` / `faithful-unverified`;
  publishable as a quality annotation in the dataset.
- **Sampled precision audit per phase**: N = 200 random triples manually
  reviewed (mentors + contributor) before the next phase unlocks; publish the
  audited precision with the dataset.
- **Open-domain caveat, stated honestly**: benchmark F1 was measured with
  per-domain ontology bounding; production runs rank over the full DBpedia
  ontology (already supported). Phase 0/1 exist precisely to measure quality in
  the open-domain setting before real money is spent.

## 7. Output and publication

- Expected yield ≈ 2–3 extracted triples/sentence → **≈ 20–30 M triples** for
  the full corpus, ≈ 3–5 GB as N-Triples.
- Published to the **DBpedia Databus as a versioned dataset (triples only)**,
  with per-triple provenance (source sentence ID + verification status);
  regenerable per Wikipedia/DBpedia release cycle.
- The stack remains distributed as the Docker image (GHCR), reproducible from
  this repository + Databus source artifacts.

## 8. Phased plan with decision gates

| Phase | Deliverable | Cost | Gate to proceed |
|---|---|---|---|
| 0 | 100 abstracts through the deployed stack; traced outputs shared for mentor review | < $2 | mentors judge output quality |
| 1 | 100 k abstracts + 200-triple precision audit + open-model benchmark re-run | ≈ $1 k | audited precision acceptable; Option A vs B decision |
| 2 | 1 M abstracts, first Databus release (beta) | ≈ $10 k | community/DBpedia review of beta dataset |
| 3 | Full corpus + versioned Databus release | ≈ $41–51 k (A) or ≈10× less (B) | — |

**The ask to DBpedia**: sponsor Phase 1 (≈ $1 k + review time). Phases 2–3 only
on the strength of Phase 1's audited numbers.

## 9. Risks, honestly

| Risk | Mitigation |
|---|---|
| Open-domain quality below benchmark quality | Phase 0/1 measure it before scale; precision audits gate every phase |
| API provider variance / rate limits | measured at macro ±0.005 on the benchmark; self-hosted Option B removes it entirely |
| Cost estimate drift | unit cost is measured, not modeled; invoices attached per phase |
| Abstract parsing artifacts (junk literals observed in snapshot) | length/character filters (already applied in our sampling); counted into yield estimates |

## Appendix A — traced examples (first Phase-0 batch, run 2026-08-10)

Three abstracts — a person, a place, an organisation — through the **deployed
container** (`nef2` image, real index + store). Raw request/response JSON:
[`examples/phase0_results.json`](examples/phase0_results.json).
Timing: 30–74 s/abstract, consistent with the benchmark's ≈27 s/sentence.

**1 · Person (long-tail, diacritics, dates)** — *"Józef Franciszek Darzyn
Ciemiński (Borzyszkowy, 4 August 1867 – Winona, 1959) was a Polish-born Roman
Catholic priest…"* → 8/8 triples, all gate-approved:

```
Józef_Franciszek_Darzyn_Ciemiński  birthPlace   Borzyszkowy
Józef_Franciszek_Darzyn_Ciemiński  birthDate    1867-08-04
Józef_Franciszek_Darzyn_Ciemiński  deathPlace   Winona
Józef_Franciszek_Darzyn_Ciemiński  deathDate    1959
Józef_Franciszek_Darzyn_Ciemiński  nationality  Polish
Józef_Franciszek_Darzyn_Ciemiński  religion     Roman_Catholic
Józef_Franciszek_Darzyn_Ciemiński  occupation   Roman_Catholic_priest
Józef_Franciszek_Darzyn_Ciemiński  location     Minnesota
```

An obscure entity, diacritics intact, prose date normalised to `1867-08-04` —
the exact profile infobox mappings miss.

**2 · Place** — *"Medamarthy is a village in Srikakulam district of Andhra
Pradesh in India."* → the full containment chain, 4/4 approved:

```
Medamarthy           type      Village
Medamarthy           isPartOf  Srikakulam_district
Srikakulam_district  isPartOf  Andhra_Pradesh
Andhra_Pradesh       country   India
```

**3 · Organisation (honest case)** — *"Winston-Salem State University (WSSU), a
constituent institution of the University of North Carolina…"* → 9 extracted,
2 rejected by the gate, 7 kept — of which 4 are solid
(`isPartOf University_of_North_Carolina`, `location`, `country`, `member`) and
**2–3 are marginal**: open-domain predicate drift produced
`programCost "baccalaureate programs, graduate programs"` and a vacuous
`student "diverse student population"`.

**Reading for reviewers.** Entity linking and place/person relations hold up at
benchmark quality on real abstracts; the known gap is predicate selection
without per-domain ontology bounding (the benchmark supplied bounded predicate
lists; open-domain ranking over the full ontology is looser). This is precisely
what the Phase-1 precision audit measures — and the audit gate exists so that
this class of triple is quantified, filtered (e.g. minimum-informativeness rule
for literal objects), or fixed before any large spend.

## Appendix B — sources

- Workload counts/samples: SPARQL queries in §3 against our snapshot (load
  manifest in [REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md)).
- Unit cost: measured benchmark spend (OpenRouter pricing page, 2026-08;
  invoice to be attached).
- Benchmark result and variance: [REPORT.md](REPORT.md), tag `final-results-0.6317`.
- NEF 1.0 baseline cost: mentor-reported (≈$30–35 full benchmark), exact figure
  to be confirmed by mentors.
