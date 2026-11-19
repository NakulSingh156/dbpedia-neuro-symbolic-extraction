# Friday update for Tsoru — 6 November 2026

## The project goal

We want text-to-KG systems to keep facts about people or things even when the text does not give their names. The graph should use a named entity when evidence supports one, and an anonymous node when the identity is unclear or absent.

## What we built this week

- A first dry-run set of **16 source-linked sentences** from 16 biography pages. **11** can be resolved from article context; **5** describe a person the article does not name.
- A reproducible Wikidata evidence capture for all 16 anchor entities. It saves the article revision IDs, relevant relationship claims, English labels, the raw API responses, capture time, and SHA-256 hashes. It is a small dated evidence slice, not a full Wikidata dump.
- The capture script is in the folder so we can repeat the same steps later.

## What the first capture shows

- For the named examples, Wikidata records the expected parents or spouse in many cases. For Zoë Heller, it records her father but not a mother claim in this capture. These are evidence checks, not accuracy scores.
- For the five unnamed-in-article sibling cases, the captured anchor claims return no sibling, or a sibling who does not fit the sentence: Indira Gandhi has none; Alfred d’Orsay lists Ida, not the brother; Charles Martin Hall lists Julia, not a brother; James Seth and Jennie Carter have no sibling claim in the capture. An absent claim does not prove the person never existed.
- A separate archive resolves Charles Hall’s deceased brother as **Louis Albert Hall**, while the article itself leaves him unnamed. An independent Cardiff biography confirms James Seth’s unnamed elder brother; it still does not provide a name. The original newspaper item behind Jennie Carter’s example remains to be found.

## What this means for the method

The method should keep two kinds of evidence separate: what the input article says and what the knowledge base records. A person can be identifiable from a separate source even when the article and KB do not name them. We should not treat a missing KB link as proof that no real person exists.

## Decisions to make together

1. Is a dated capture of the exact Wikidata claims enough for this pilot, or should we restore the project’s local DBpedia 2022-12 service and use that as the main KB?
2. For Charles Hall, should the gold answer use Louis Albert Hall from the archive, while scoring the system’s article+KB output separately?
3. Should examples include the whole article as context, or only the sentence? The answer changes whether the 11 context-resolved examples count as named or anonymous.
4. Should multi-person facts such as “his parents married” be included as a relation path, or left out of the first benchmark?
5. Can a second annotator review the pilot before we freeze the first 100 examples?

## Next steps after the meeting

- Apply Tsoru’s decisions to the annotation rules.
- Finish the original-source and licence checks, especially for Jennie Carter.
- Have two annotators label the 16 examples and resolve disagreements.
- Expand to a manually checked 100-sentence benchmark, then run the cheap-model baseline and ordinary Text2KGBench no-harm check.

## Files for review

- [Pilot candidates and annotations](/Users/nakul/Desktop/GSoC%202026/DBpedia/knowledge_graph_pipeline/research/anonymous_nodes/testset/post_tsoru/pilot_candidates_v0.csv)
- [Evidence slice and raw captures](/Users/nakul/Desktop/GSoC%202026/DBpedia/knowledge_graph_pipeline/research/anonymous_nodes/testset/post_tsoru/wikidata_slice_2026-11-04/)
- [Relation summary](/Users/nakul/Desktop/GSoC%202026/DBpedia/knowledge_graph_pipeline/research/anonymous_nodes/testset/post_tsoru/wikidata_slice_2026-11-04/relation_summary.csv)
- [Capture manifest](/Users/nakul/Desktop/GSoC%202026/DBpedia/knowledge_graph_pipeline/research/anonymous_nodes/testset/post_tsoru/wikidata_slice_2026-11-04/capture_manifest.json)
- [Capture script](/Users/nakul/Desktop/GSoC%202026/DBpedia/knowledge_graph_pipeline/research/anonymous_nodes/testset/post_tsoru/freeze_wikidata_pilot.py)
