# Decisions — anonymous-node grounding paper

Every gate outcome and design decision, dated. Newest first.

| Date | Decision | Why | Who |
|---|---|---|---|
| 2026-10-16 | Wikidata survey population = items with an English Wikipedia article | Matches DBpedia's universe, so the KBs are compared on the same entities | Nakul (+ Claude) |
| 2026-10-16 | Identity compared QID-to-QID via the Wikipedia API | Local store has no redirect table; DBpedia 2022 names are often redirects now | Nakul (+ Claude) |
| 2026-10-16 | DBpedia→Wikidata property mapping = ontology `owl:equivalentProperty` + 5 documented manual mappings | Ontology covers 58% of Phase-1 volume; manual set kept small and reported separately | Nakul (+ Claude) |
| 2026-10-09 | Target ISWC 2027 research track; generic-ontology scope | Tsoru meeting | Nakul, Tsoru |
