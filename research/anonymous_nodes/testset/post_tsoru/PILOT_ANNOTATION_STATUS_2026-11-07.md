# Pilot annotation status — 7 November 2026

We have moved from a 16-row candidate list to a first-pass annotation worksheet tied to the dated Wikidata evidence capture.

## Current state

- 16 sentences from 16 linked biography pages; all anchor QIDs and article revision IDs are recorded.
- 11 cases are resolvable from article context. Of those, 9 have straightforward named graph targets, one has a mother QID still to resolve, and one describes a relation between two parents.
- Four cases are straightforward anonymous-node candidates at first pass: Indira Gandhi’s younger brother, Alfred d’Orsay’s elder brother, James Seth’s elder brother, and Jennie Carter’s younger sister.
- Charles Martin Hall’s brother is the policy edge case: the input article and captured anchor claims do not name him, but Oberlin College Archives identifies him as Louis Albert Hall.
- No candidate QIDs fit the five sibling descriptions in the captured anchor claims. The captured facts for Alfred and Charles are sisters, not the described brothers.
- All labels remain proposals pending a second annotator. No metric has been calculated.

## Files

- `pilot_first_pass_annotations_v0.csv` — sentence, context, captured KB evidence, proposed edges, and review flags.
- `PILOT_ANNOTATION_GUIDE_V0.md` — what each field and decision label means.
- `wikidata_slice_2026-11-04/` — raw API responses, relation summary, and capture manifest.

## Next annotation tasks

1. Resolve Caroline Heller’s entity ID in DRY-003.
2. Decide whether DRY-012 and DRY-014 belong in the first benchmark and how to score them.
3. Locate and cite the original source for DRY-016.
4. Ask a second annotator to review the whole sheet, then adjudicate disagreements.
5. Use the agreed rules to add examples toward the 100-sentence pilot.
