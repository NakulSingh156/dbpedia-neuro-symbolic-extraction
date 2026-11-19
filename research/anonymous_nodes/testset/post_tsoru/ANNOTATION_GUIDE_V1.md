# Annotation guide v1 — anonymous-node KG benchmark (19 Nov 2026)

Replaces `PILOT_ANNOTATION_GUIDE_V0.md` for all new annotation. The policies marked **[confirm with Tsoru]** are proposals for the 20 Nov meeting. Until he confirms them, labels made under them stay provisional.

## 1. What the benchmark tests

A text-to-KG system reads a source article and must produce KG facts. When a fact involves a person or thing that the sentence does not name, the system must:

- **name** it, when the article or the KB supports exactly one identity;
- create an **anonymous node** with a **candidate list**, when several identities fit;
- create an **anonymous node** marked **missing**, when nothing in the input identifies it;

and it must **never drop the fact or invent an identity**.

## 2. Two phenomena — label them separately **[confirm with Tsoru]**

| Type | What the text does | Example | Can a system ever name it? |
|---|---|---|---|
| **R — relational description** | Refers to a real entity it does not name, through a relation to a named or topic anchor | "Another younger brother died in infancy." (Lord Dunsany) · "an unnamed Russian IT company" | Yes, if the article or KB identifies it |
| **U — stated-unknown identity** | States that the identity is unknown or anonymous | "His parents are unknown." · "The papyrus's author is anonymous." · "an unidentified artist" | No, by construction: the correct output is always an anonymous node |

Why separate them: type U is always "anonymous node, status unknown". Mixing it with type R would inflate the anonymous-node scores and hide whether the system can tell the cases apart. We report R and U separately, plus combined.

## 3. What the system is given **[confirm with Tsoru]**

- **Input:** the **whole article** at a recorded revision ID, plus the **frozen KB evidence** (the dated Wikidata slice; DBpedia 2022-12 when used).
- **Gold is defined relative to that input.** A perfect system reading the article and querying the frozen KB should produce the gold output.
- **External evidence is recorded but not used for main scoring.** Example: Charles Martin Hall's brother is named by an archive, but not by the article or Wikidata. Record it as `world_identity` with the source. It feeds a separate "KB-completion potential" analysis (the fact could be added to Wikidata).

## 4. Outcome label per target (one label per described entity)

| Label | Meaning | Correct system output |
|---|---|---|
| `NAMED_IN_CONTEXT` | The article names the entity elsewhere (apposition, another sentence, a family list) | The named entity (KB QID if one exists) |
| `KB_UNIQUE` | The article does not name it; the frozen KB has exactly one value that fits the relation and gender | That QID, with the grounding tier: schema-unique if the property has a single-value constraint, else data-unique |
| `KB_AMBIGUOUS` | Several KB values fit | Anonymous node + candidate list |
| `KB_MISSING` | The anchor is in the KB; no value fits | Anonymous node, status missing |
| `KB_UNKNOWN_VALUE` | The KB itself has an "unknown value" (somevalue) for the relation | Anonymous node aligned to the KB's unknown value |
| `ANCHOR_NOT_IN_KB` | The anchor has no KB item | Anonymous node, status unresolved |
| `TEXT_UNKNOWN` | Type U: the text says the identity is unknown | Anonymous node, status unknown |
| `EXCLUDE` | Not a valid item (see §7) | — |

A candidate must fit the relation **and** its constraints (gender, role, ordinal). A sister is not a candidate for "his brother".

## 5. Hard cases

1. **Several unnamed entities** ("two brothers", "his parents", "three unnamed siblings") **[confirm with Tsoru]**
   - Count stated and ≤ 3: **one anonymous node per individual**, e.g. two brother nodes.
   - "Parents": two nodes, father and mother, when the text implies both.
   - Otherwise: **one group node** with `cardinality` (exact if stated, else unknown).
   - Score per node.
2. **Pseudonyms and notnames** ("Master of the Legend of Saint Bruno", byline "Vidi")
   - If the KB has an item for the notname, which Wikidata often does, it is an entity: label `KB_UNIQUE` for that item.
   - Otherwise: an anonymous node carrying the string as its label, flag `pseudonym`.
3. **Disputed or speculative identities** (competing theories about Maxime Weygand's parents; *Go Ask Alice*; *O: A Presidential Novel*)
   - Anonymous node + the text's proposed identities as `proposed_identity` candidates, flag `stress`.
   - **Stress items are reported separately and excluded from the main metrics.** **[confirm with Tsoru]**
4. **Multi-entity relations** ("his parents married in 1850") **[confirm with Tsoru]**
   - Keep only if every entity is representable: two parent nodes plus a spouse edge between them.
   - Otherwise `EXCLUDE` from the first 100.
5. **Biological vs adoptive / step relations**
   - Use the precise relation: father (P22) vs stepparent (P3448) vs adoptive parent.
   - Never fill a biological slot with an adoptive parent named in the next sentence.
6. **Fiction** (characters in film plots, soap operas): `EXCLUDE` from the main set, or tag `fiction` for a stress subset.
7. **Historical uncertainty** ("possibly", "is thought to"): keep the fact only if the text asserts the entity exists. Flag `hedged`.
8. **"Another / other / an unnamed X" excludes the entities named in the article.** Candidates are the KB values that fit, **minus** those the article names for the same relation.
   - Lord Dunsany's "another younger brother" cannot be his named brother.
   - Francesco Sforza's "one unnamed child died at birth" cannot be any of his named children: `KB_MISSING`, not `KB_AMBIGUOUS` (found in triage, 19 Nov).
9. **Every attribute in the description constrains the candidates**: nationality, time, ordinal, role. Snowden's "an unnamed Russian IT company" is not any of his recorded employers. If an attribute cannot be checked against the KB, the annotator decides and writes a note.
10. **The KB contradicts the text.** If the text says the identity is unknown or disputed but the KB asserts one (Ptolemy XII's mother: text uncertain, Wikidata says Cleopatra IV), label from the text (`TEXT_UNKNOWN`), record the KB value as a candidate, and flag `kb_text_conflict`. **[confirm with Tsoru]**

## 6. What every row records

`item_id, phenomenon (R/U), article, revision_id, sentence, target_span, anchor (text + QID), relation path (KB properties), outcome label, gold target (QID / anonymous node id), candidate QIDs, anonymous status, flags (stress / pseudonym / hedged / fiction / multi), world_identity (+ source), evidence slice id + sha256, annotator, second annotator, adjudication.`

## 7. Exclude

- References to the article's own topic ("He", "the film").
- Generic or class mentions ("many fans", "a village").
- Negated or hypothetical entities ("he had no brother").
- Entities named in the same sentence.
- Sentences whose relation cannot be mapped to any KB property in the inventory.

## 8. Splits, freeze, reliability

- **Split by article, never by sentence:** dev 20% / test 80%.
- **The test split is frozen and hashed before any tuning.**
- **Annotation:** Annotator 1 is Nakul (human). An LLM pre-annotation may be shown **only after** the human's labels are saved. Annotator 2 reviews all rows; disagreements are adjudicated.
- **Report** Cohen's κ on the outcome label and exact-match agreement on the gold target.
- **Licence:** Wikipedia text is CC BY-SA 4.0. Keep the revision ID and attribution for every row.
