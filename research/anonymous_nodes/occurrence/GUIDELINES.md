# Occurrence annotation guidelines (v1.1, 2026-10-16 — kb_entity flag, T-ZERO and exclusions clarified after batch 1)

**Question:** does this sentence refer to an entity *without naming it in this sentence*?
Read the sentence with its abstract's **topic** (the abstract's own entity) and the **previous sentence**.
An entity is something that could plausibly be a KB entity: a person, place, organisation, work, event, taxon, product…

## Labels (a sentence can carry several; record each unnamed reference)

| Label | Meaning | Example |
|---|---|---|
| **T-PRON** | Pronoun or possessive for the topic | "**He** was born in Chester." (topic: Bill Rigby) |
| **T-DEF** | Definite or descriptive NP for the topic | "**The film** was made by Wien-Film." |
| **T-ZERO** | The topic takes part in a fact stated here but isn't referred to at all — including attribute sentences | "Filming took place in Los Angeles." · "The wingspan is about 20 mm." · "As of the 2000 census, the population was 153." |
| **O-PRON** | Pronoun for a non-topic entity | "…met Ruth. **She** later…" |
| **O-REL** | A non-topic entity picked out by its **relation to another entity**, not named in this sentence | "**her husband**", "**his father**", "**the band's drummer**", "**the club's chairman**", "**its capital**" |
| **O-DESC** | A non-topic entity described without a relational anchor | "**a local merchant**", "**the first building in Tibet**" |

## Flags on O-REL (the paper's core case)

- `named_elsewhere`: is the entity named anywhere else in the abstract (e.g. apposition "his brother, Alexander")? yes / no
- `plural`: does it refer to a group ("his three sons")? yes / no
- `relation`: the relation in plain words (spouse, father, member, capital, …)
- `kb_entity`: would this referent plausibly have its own KB entry? likely / unlikely (a person or work: usually likely; an event such as "the trial of X" or a group such as "the staff of X": usually unlikely). Also recorded on O-DESC.

## Do NOT label

- Generic or non-referential NPs: "people", "many species", "a number of awards", "the public".
- Classes and kinds: "a village", "an American actor" (these classify the topic, they don't refer to a new entity).
- Times, quantities, measures.
- An entity named in the sentence, even by a partial name or alias ("the U.S.", "Rigby", "the capture of Harfleur").
- A pronoun whose antecedent is named in the same sentence ("Blackey … one of its citizens").
- A sentence whose only link to the topic is loose context (a team relegated in the topic tournament) — no T-ZERO unless the natural triple has the topic as subject or object.

## Output

Per sentence: `{"id", "labels": [{"type", "span", "relation"?, "named_elsewhere"?, "plural"?}], "note"?}`; an empty list means no unnamed reference.

## Reliability

First pass by Claude (an LLM, not a human annotator). A random 50 are to be labelled blind by Nakul; report Cohen's κ on "has any unnamed reference" and on the O-REL decision before any number is cited.
