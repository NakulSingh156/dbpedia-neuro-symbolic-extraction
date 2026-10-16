# Decisions — anonymous-node grounding paper

Every gate outcome and design decision, dated. Newest first.

| Date | Decision | Why | Who |
|---|---|---|---|
| 2026-10-16 | Every grounding carries a tier: schema-unique (single-value constraint / functional) vs data-unique; metrics reported per tier | Open-world objection; like-for-like agreement 90.1% vs 78.4% | Nakul (+ Claude), to confirm |
| 2026-10-16 | Add M2b in-document resolution before the KB; KB verifies text-resolved cases | 25–31% of real descriptions are named or inferable elsewhere in the text | Nakul (+ Claude), to confirm |
| 2026-10-16 | Natural set mined from full biography articles, fiction filtered | Same density as abstracts but ≈6× more cases per person | Nakul (+ Claude), to confirm with Tsoru (decision 4/7) |
| 2026-10-16 | Proposed story emphasis: facts kept + long-tail recall + tiered abstention, not "LLMs hallucinate"; B1 run in two modes | Teaser: 7–8B LLMs abstained rather than inventing names when UNKNOWN was allowed (n=23) | to decide with Tsoru (decision 8) |
| 2026-10-16 | Answer comparison in the grounder must be convention-aware: demonym→country, historical polity→successor, subclass (P279) and sport↔player equivalences, plus containment | 52% of Wikidata residual mismatches are the same fact modelled differently; without this, Wikidata looks 38 points worse than it is | Nakul (+ Claude), to confirm |
| 2026-10-16 | Test set will be **mined** (pattern scan + hand check), not drawn at random | O-REL is 2.7% of abstract sentences, and KB-groundable cases are ~0.2–1%; a random draw would be almost all negatives | Nakul (+ Claude), to confirm |
| 2026-10-16 | Topic-coreference cases (40% of sentences) are out of scope for the paper's core claim | Already handled by coref tiers 1–3; not a grounding problem | Nakul (+ Claude), to confirm |
| 2026-10-16 | Wikidata survey population = items with an English Wikipedia article | Matches DBpedia's universe, so the KBs are compared on the same entities | Nakul (+ Claude) |
| 2026-10-16 | Identity compared QID-to-QID via the Wikipedia API | Local store has no redirect table; DBpedia 2022 names are often redirects now | Nakul (+ Claude) |
| 2026-10-16 | DBpedia→Wikidata property mapping = ontology `owl:equivalentProperty` + 5 documented manual mappings | Ontology covers 58% of Phase-1 volume; manual set kept small and reported separately | Nakul (+ Claude) |
| 2026-10-09 | Target ISWC 2027 research track; generic-ontology scope | Tsoru meeting | Nakul, Tsoru |
