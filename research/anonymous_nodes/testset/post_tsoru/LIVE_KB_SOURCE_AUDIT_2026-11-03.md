# Pilot source and KB audit — 3 November 2026

This is a dry-run evidence log for the 16 candidate sentences, not a gold annotation file. It separates what the input article says from other source evidence and live KB observations. No graph labels have been adjudicated.

## KB setup found in the project

- The Wikidata adapter in `research/anonymous_nodes/generic/kb_wikidata.py` queries live QLever, with Wikidata Query Service as fallback. It caches results by a hash of endpoint and query, but does not store a dated KB release or retrieval timestamp in each result.
- The project documents a local DBpedia snapshot from 2022-12 at `http://localhost:7878/query`. That endpoint did not respond during this audit, and the local Docker daemon is unavailable, so the snapshot could not be queried.
- Therefore, none of the rows may yet be labeled `missing_fact` against a pinned snapshot. A live query is only a dated observation and can change.

## Unnamed sibling cases

| Item | Input article evidence | Other source evidence | Live Wikidata observation | Annotation status |
|---|---|---|---|---|
| DRY-004 Indira Gandhi | Says a younger brother died young, without a name. | No name found in reviewed article/source context. | Q1149 page has no sibling statement in the available page extraction. | Anonymous-node candidate; pinned query pending. |
| DRY-013 Alfred d’Orsay | Says elder brother died in infancy, without a name. | [ODNB entry](https://academic.oup.com/oxford-dictionary-of-national-biography/reference/63486/reference-article-abstract/580019793) independently confirms the fact but does not name him. | Q2622452 lists sister Ida d’Orsay; no male sibling answering the sentence surfaced in page extraction. | Anonymous-node candidate; pinned query pending. |
| DRY-014 Charles Martin Hall | Says one of two brothers died in infancy, without identifying which. | [Oberlin College Archives](https://oberlin.libraryhost.com/repositories/2/resources/623) lists Louis Albert Hall (1855–1862) and George Edward Hall (1851–1921); this resolves the deceased brother as Louis Albert Hall from external archival evidence. | Q443131 lists Julia Brainerd Hall, but no male sibling. | The article input remains unnamed; external gold evidence identifies Louis Albert. Keep separate until annotation policy is settled. |
| DRY-015 James Seth | Says an elder brother died in infancy, separately from named brother Andrew. | [Cardiff biography of Andrew Seth Pringle-Pattison](https://sites.cardiff.ac.uk/collingwood/files/2013/11/Andrew-Seth-Pringle-Pattison-biography.pdf) independently confirms an elder brother died in infancy but does not name him. | Q11309438 could not be verified through available page extraction. | Anonymous-node candidate; source fact has cross-source support, identity remains unknown. |
| DRY-016 Jennie Carter | Says younger sister died at age ten, without a name. | The article attributes the incident to Carter’s writing in *The Elevator*, but the exact original issue was not located in this audit. | Q28777198 could not be verified through available page extraction. | Hold for primary-source check; do not assign a final missing label yet. |

## Reproducible next action

Choose one KB evidence policy for the pilot: (A) restore and use the documented DBpedia 2022-12 store, or (B) freeze the Wikidata claims needed for each anchor as dated JSON/API captures with endpoint, query, retrieval time, and file hash. Then rerun the relation checks and have a second annotator review the five sibling rows before filling gold graph fields.
