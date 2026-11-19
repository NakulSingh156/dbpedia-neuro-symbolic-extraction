# Anonymous-Node KG Benchmark — Start Plan v0

**Prepared 3 November 2026.** This is an execution note based on Tsoru's latest meeting decisions. It supplements the existing methodology; it does not replace or silently revise the earlier draft.

## 1. Main question

Can a text-to-knowledge-graph system preserve facts about entities that the text does not name by creating valid anonymous graph nodes—and does that improve graph completeness without making the graph less correct?

Finding a real-world identity is supporting behavior. Use a name when evidence supports one identity. If evidence leaves several possibilities or no recorded answer, preserve the fact using an anonymous node and mark its status. Measure whether this helps; do not assume it helps.

## 2. What already exists

- A prototype controlled set has **575 template examples**; a paraphrased check handled **572/575**, with no wrong identity choices and three abstentions. These were development/plumbing checks, not a final manually checked benchmark.
- A natural development batch has **59 verified target descriptions from 45 biographies**. The detector was tuned on this batch, so these examples must stay in development and must not be counted as fresh held-out test data.
- The survey reviewed **14 extraction benchmarks** and hand-checked **120 possible examples**. It found no example of our exact target: a non-topic entity described through a relationship to a named anchor. Text2KGBench remains useful for a standard no-harm check on ordinary text-to-KG extraction.

Keep those assets; label their role clearly. Build the new gold set separately.

## 3. First milestone: a manually checked 100-sentence pilot

Start with 100 sentences, then expand toward 300–500 only after the annotation rules work reliably. The pilot should include real text and controlled examples, plus a small set of ordinary sentences without a target description to catch false detections. Record the source and licence for every item.

For target cases, include examples where:

- the surrounding text identifies the entity;
- the knowledge base supports one identity;
- the knowledge base returns several candidates;
- the knowledge base has no answer; or
- the description or anchor cannot be interpreted safely.

Use existing examples as development material where appropriate. Collect fresh source material for held-out evaluation. Split by article/person/source—not by sentence—so nearby sentences from one biography cannot leak across splits. Freeze the test split before tuning.

## 3a. Candidate dry-run pack (3 November)

`pilot_candidates_v0.csv` contains 16 sentence candidates from 16 biography pages, with source links and draft target spans. None of the people overlap with the existing 45-biography development batch. Five sentences appear to describe an entity without naming it in that sentence; the remaining candidates mainly test whether article context supplies the name. These are **not gold labels**: full-page context, KB evidence, source/licence details, and graph edges still need checking. Use them to rehearse the annotation rules only.

### 3b. Source-context review (3 November)

The 16 dry-run sentences were checked against their linked biography pages and nearby article context. Eleven have a target identity named elsewhere in the article. Five do not name the described person in the article text: Indira Gandhi’s younger brother, Alfred d’Orsay’s elder brother, one of Charles Martin Hall’s two brothers, James Seth’s additional elder brother, and Jennie Carter’s younger sister. An Oberlin College Archives family list identifies Charles Hall’s deceased brother as Louis Albert Hall (1855–1862), using the names and dates of his siblings. This is external evidence, not a name present in the input article. The James Seth sentence has a citation-quality concern and should be held out until its underlying source is checked. Indira, Alfred, James, and Jennie remain useful anonymous-node candidates pending source and KB review. For James, an independent Cardiff biography supports the fact but also leaves the person unnamed. For Jennie, the exact original newspaper item still needs to be located. For Charles Hall, the archive supplies a name externally, while the input article and current Wikidata item do not.

Live Wikidata page checks (3 November 2026) showed no sibling statement on Indira Gandhi’s item, Ida d’Orsay but no male sibling on Alfred d’Orsay’s item, and Julia Brainerd Hall but no male sibling on Charles Martin Hall’s item. These are current-page observations, not checks against the project’s pinned snapshot. The dated audit note records endpoints and limits.

### 3c. KB snapshot availability

The current Wikidata adapter uses live QLever and Wikidata Query Service endpoints and caches query results by hash; it does not pin a dated Wikidata release or record a retrieval time with each cached result. The project documents a DBpedia 2022-12 local snapshot, but its local SPARQL service on port 7878 was unreachable during this review. Therefore no candidate is yet labeled as missing from a pinned KB. Before gold annotation, either restore the documented local DBpedia service or freeze the Wikidata item claims used for this pilot (including retrieval date, endpoint, query, and file hash).

All candidate graph labels remain blank. The evidence notes in the CSV record the distinction between article context and KB evidence.

### 3d. Dated Wikidata evidence capture (4 November)

A relevant-claims evidence slice has now been captured for all 16 anchors through the Wikidata API. The package stores the raw Wikipedia pageprops/revision responses, article revision IDs, raw Wikidata claim/label responses, retrieval times, exact API URLs, and SHA-256 hashes. The selected properties are father (P22), mother (P25), spouse (P26), sibling (P3373), child (P40), and relative (P1038). This is a frozen query-result slice for these examples, not a full Wikidata dump or a claim about all Wikidata facts.

The 11 context-resolvable examples mostly have matching parent or spouse claims. Zoë Heller’s father appears, while the mother claim is absent from the capture. Of the five article-unnamed sibling examples, the captured anchor item gives no sibling claim for Indira Gandhi, James Seth, or Jennie Carter; Alfred d’Orsay lists Ida but not the described brother; Charles Martin Hall lists Julia but not a brother. Absence of a direct claim is not proof that the relation is false. Keep graph labels in draft until annotators review the evidence and the source policy.

The capture script, raw responses, relation summary, and manifest are in `wikidata_slice_2026-11-04/`. Use this date and hash as the pilot KB evidence version.

## 4. What annotators record

For each sentence, record:

1. sentence and enough surrounding context to understand it;
2. source, article/person ID, and licence or source note;
3. the described entity span, named anchor span/ID, and relation or relation path;
4. whether the identity is stated in context, uniquely supported by the KB, ambiguous, missing from the KB, or unresolved;
5. the gold graph edge(s): named entity ID when justified, otherwise a stable anonymous-node ID;
6. for anonymous nodes: type if known, description text, candidate IDs if any, and status (`ambiguous`, `missing_fact`, or `unresolved`);
7. evidence and annotator notes, plus second-review/adjudication fields.

Keep **text evidence** and **KB evidence** as separate fields. A sentence can identify someone from context even when a limited KB query returns multiple candidates. The Marie Antoinette sentence is a useful training example: a spouse-only query returns two candidates; the 1793 clue can distinguish Louis XVI if the system can map and verify that clue. Do not label the system as successful on that step until it has been evaluated end to end.

## 5. How to judge the systems

Primary measures:

- **Correct facts kept:** relevant facts appear in the output graph rather than being dropped.
- **Correct graph structure:** the right anchor, relation, direction, and target node are connected.
- **Anonymous-node quality:** an unnamed fact gets a well-formed anonymous node with the right status and candidates where applicable.
- **Wrong-name rate:** the system does not attach a real identity when the evidence does not support it.
- **Junk-node rate:** descriptions such as “brother of X” are not emitted as if they were entity names.
- **Standard benchmark check:** run the same NEF/text-to-KG system on Text2KGBench with the anonymous-node feature off and on; check that ordinary triple F1 does not fall.
- **Cost and speed:** model calls, time, and cost per 1,000 sentences.

Report both graph quality and fact preservation: keeping extra unsupported triples must not count as an improvement.

## 6. Comparison plan

Run every method listed in the current methodology on the same pilot and data splits: NEF as-is; LLM-only; KB-candidate ranking; LLM-generated KB query; LLM with retrieved KB facts; the proposed KB-checking method; and the hybrid. Use a cheap local/OpenRouter model first, then run the more expensive models on the same cases once the setup is stable.

For each method, test the relevant parts that could be helping: anonymous-node output, KB evidence, context clues, relation constraints, candidate handling, and safe abstention. Keep the model and data fixed when comparing methods where possible. Record model/version, prompt, settings, KB snapshot, seed, runtime, and cost for every run.

## 7. First work blocks

1. Confirm the annotation rules and final column names using 10–20 varied examples.
2. Resolve disagreements and update the guide before collecting the remaining pilot items.
3. Complete and second-check the 100-item pilot; report where annotators disagree and whether the categories are usable.
4. Freeze a held-out portion, run the cheap-model comparison, and make only evidence-based changes.
5. Expand toward 300–500 examples and run the standard benchmark no-harm check.

**First concrete action:** fill the accompanying CSV only with real, source-traceable examples. Do not invent benchmark rows to make the sheet look complete.
