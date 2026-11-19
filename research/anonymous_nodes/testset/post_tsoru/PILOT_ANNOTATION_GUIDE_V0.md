# First-pass annotation guide — anonymous-node pilot

This guide goes with `pilot_first_pass_annotations_v0.csv`. The sheet is a **single-annotator draft**, not final gold data. A second person must review the rows before evaluation.

## How to read each row

- `text_identity_status` records what the article or its nearby context tells us.
- `kb_identity_status` records what the dated Wikidata evidence slice contains.
- `first_pass_target_label` and `first_pass_target_qids` are the proposed target identity.
- `first_pass_candidate_qids` should contain only KB answers that fit the described person and relation. A sibling with the wrong gender or role is not a candidate.
- `first_pass_graph_edges_json` records directed triples. Predicates use plain names such as `father`, `mother`, `spouse`, and `sibling` for this annotation pass.
- Anonymous IDs such as `_:DRY-004-T1` are stable within this pilot row. They do not claim the real-world identity is unknowable; they preserve the fact when the input-plus-KB evidence does not support a name.

## Draft decision labels

- `named`: the article context gives a name and the captured KB claim supports that relation.
- `missing_fact`: the text says the entity exists and the relation is clear, but the captured KB slice has no fitting answer. This describes the KB evidence, not whether the real-world fact is true.
- `policy_pending`: use only in this draft where the gold policy is unsettled. DRY-014 is the example: an outside archive gives a name that neither the input article nor the captured Wikidata relation gives.
- `unresolved`: reserve for cases where we cannot safely identify the anchor or relation.

## Rows that need decisions or extra review

- **DRY-003:** article context names Caroline Heller, but her QID is not in the captured claims; find and verify it before final gold.
- **DRY-012:** the sentence describes the marriage of two parent entities. Decide whether this multi-entity relation belongs in the first benchmark, and verify the spouse edge if retained.
- **DRY-014:** decide whether external archival evidence may determine the gold identity when the evaluated system only sees the article and KB.
- **DRY-016:** locate the original *Elevator* source before treating the claim as final gold.
- All rows need a second annotator; disagreements need adjudication.
