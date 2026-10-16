# Contribution statement — DRAFT v0 (2026-10-16)

**Provisional.** Written after related-work pass 1 (search-level, no full reads). Revise after pass 2, especially after reading implicit entity linking (Perera et al. 2016), and agree with Tsoru at gate G1.

## Draft abstract paragraph

Text-to-knowledge-graph extraction handles entities that a sentence names. When a sentence refers to an entity only through its relation to another one — *"Marie Antoinette's husband was killed in the war"* — extractors either drop the fact or name an entity the text never mentioned. We propose **anonymous-node grounding**: the description is compiled into a constraint query against the target knowledge base, and the entity is named only when the KB returns exactly one answer (after collapsing values that merely contain one another). Otherwise the fact is kept with a provenance-tagged anonymous node: carrying the candidate set when the KB is ambiguous, and flagged as a missing fact when the KB records nothing. The approach is ontology-agnostic through a thin adapter layer, shown on DBpedia and Wikidata. We contribute (i) the formulation and a measurement of how often such descriptions can be grounded on two KBs; (ii) the first test set for relational descriptions of unnamed entities, stratified by entity popularity and answerability; and (iii) a neuro-symbolic grounding method compared against LLM-only and LLM-plus-KB-query baselines on accuracy, abstention and cost.

## Research questions

- **RQ1** How often can an unnamed entity in text be grounded uniquely, and how does that depend on the KB and the relation?
- **RQ2** Does KB-constrained grounding with abstention beat LLM-only and LLM-plus-KB-query baselines — especially on long-tail entities and when nothing is recorded?
- **RQ3** Can one architecture serve different ontologies through adapters without per-KB redesign, and at what cost?

## Evidence so far (2026-10-09 → 2026-10-16)

- DBpedia: 77.3% of extracted relational facts involve a relation that is unique up to containment, but DBpedia records the relation for only 22.8% of them → ~17% expected grounding (`results/`, `coverage.py`).
- Existing benchmarks: Wikidata-TekGen has ≈10% unnamed entity mentions (17.7% of test sentences), almost all the article's own topic ("The film …"); DBpedia-WebNLG ≈0.1%; **neither contains a relational description of another entity** (0/120 hand-labelled) (`benchmarks/`).
- Wikidata natively models "a value that exists but whose identity is unknown" (PropertySomeValueSnak), now exported as skolem IRIs — a representation precedent.
- Wikidata survey: on the same 2,271 facts, Wikidata grounds 47–49% vs DBpedia 19–21%; father/mother are 99.6% unique. When a KB answers, it agrees with the text ~96% (Wikidata) / ~98% (DBpedia) once granularity and modelling conventions are accounted for (`wikidata/`).
- Open world: where Wikidata declares a relation single-valued, the KB answer matches the text 90.1% vs 78.4% when it is only unique in the data (place relations).
- Teaser (n=23 real descriptions): Wikidata grounds 7, has nothing for 15; local LLMs mostly abstain; only the KB names 2 long-tail people. Value = facts kept + long-tail recall.
- Occurrence (first pass, κ pending): 2.7% of DBpedia abstract sentences describe another entity through a relation; ~0.2–1% are KB-groundable. **The phenomenon is sparse, so the test set has to be mined** (`occurrence/`).

## Positioning against the closest work (from pass 1)

| Work | They | We |
|---|---|---|
| Implicit entity linking (tweets) | rank a best entity for an unnamed reference | emit facts; ground only if unique; abstain with provenance; ontology-agnostic |
| KBQA + answerability (GrailQAbility) | answer questions, detect unanswerable | descriptions inside text being extracted; output an anonymous node, not "no answer" |
| Bridging anaphora | link the description to its antecedent mention | resolve the unnamed entity's KB identity and emit facts about it |
| Schema-adaptive KGC (EDC) | adapt relations to a schema | adapt to any KB for grounding unnamed entities |
| NIL prediction | named mention not in KB | unnamed mention, KB answer unique / ambiguous / absent |
