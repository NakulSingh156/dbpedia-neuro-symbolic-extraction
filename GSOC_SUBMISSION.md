# GSoC 2026 Work Product Submission — draft

*This file is the draft text for Google's final-evaluation form. The canonical
work-product URL is this repository; the full technical story is
[`REPORT.md`](REPORT.md).*

**Project:** Neuro-Symbolic Knowledge Graph Extraction for DBpedia
**Organisation:** DBpedia · **Contributor:** Nakul Singh · **Mentors:** Ara, Tommaso Soru

## What the project does

A pipeline that turns natural-language sentences into verified DBpedia triples by
combining an LLM with local knowledge-base machinery: a 16.2M-mention surface-form
index (Redis) for entity linking, a local DBpedia triple store (oxigraph) for
tiered fact verification, and train-split-learned output conventions — no
fine-tuning, and no online dependency except the LLM call itself.

## What I accomplished

- **Benchmark result:** macro F1 **0.6317** on Text2KGBench dbpedia_webnlg
  (19 domains, 2,014 sentences), matching the GPT-4o NEF baseline (0.628) at
  ~1/20th the inference cost (≈$10 vs ≈$190 for the full benchmark). Leads the
  baseline on 8/19 domains. Result is frozen at tag `v14-final` with a complete
  reproducibility bundle and archived per-sentence outputs.
- **The offline stack:** built the surface-form index from DBpedia Databus dumps;
  built and tuned the local SPARQL verification gate (~100× faster than the live
  endpoint, +0.037 macro measured); designed the faithfulness-aware multi-tier
  gate that tags every triple verified vs faithful-unverified.
- **Systematic error analysis:** offline autopsies that found and fixed, among
  others, a cross-domain literal-convention leak (food +0.22, writtenwork +0.17)
  and a title-sense disambiguation gap (film +0.24, musicalwork +0.09) — all as
  generic code paths, each fix validated offline before any paid rerun.
- **Deployment:** packaged the full stack as a public Docker service —
  `ghcr.io/nakulsingh156/dbpedia-extractor:v14` — one `POST /extract` endpoint,
  compose files for both volume and bind-mount modes, operator docs; verified
  end-to-end on a fresh host.

## Current state

Complete and reproducible: pipeline, benchmark result, documentation
(`README.md`, `REPORT.md`, `CHANGES.md`, `REPRODUCIBILITY.md`,
`deploy/DEPLOY.md`), and the published container image.

## What's left / future work

- Publish the two data snapshots (index 1.4 GB, store 15 GB) on the DBpedia
  Databus so third-party setup is fully self-serve (pending account/naming
  decision with mentors); upstream the agreed subset to the official project repo.
- Run the wikidata_tekgen half of Text2KGBench (generalisation study).
- Anonymous-node grounding ("Marie Antoinette's husband" as a constrained blank
  node, grounded via the local store only when unique) — planned as the core of
  a follow-up publication with my mentors.

## Challenges & learnings

Measurement discipline turned out to matter as much as modelling: provider-side
LLM variance at temperature 0, a host memory fault that degraded two domain runs
(caught, fixed, re-measured under a pre-declared policy), and a cross-domain
state leak that silently cost two domains ~0.2 F1 — all found by treating every
surprising number as a bug until proven otherwise.

## Links

- **Work product (this repo):** https://github.com/NakulSingh156/dbpedia-neuro-symbolic-extraction
- **Final report:** https://github.com/NakulSingh156/dbpedia-neuro-symbolic-extraction/blob/master/REPORT.md
- **Container image:** https://github.com/NakulSingh156/dbpedia-neuro-symbolic-extraction/pkgs/container/dbpedia-extractor
- **Frozen result tag:** `v14-final` / `final-results-0.6317`
