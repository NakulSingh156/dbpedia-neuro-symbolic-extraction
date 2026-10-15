# Related work — pass 1 (2026-10-16)

Roadmap step 1 (Part III, Phase 1.2). **Pass 1 = metadata and abstracts from search results and project pages; none of the papers below has been read in full yet.** Status column says what's verified. Pass 2 reads the "threat" rows in full.

## Closest prior work — the novelty threats, ranked

| # | Work | What it does | Overlap with us | How we differ (to confirm by reading) |
|---|---|---|---|---|
| 1 | **Implicit Entity Linking in Tweets** — Perera et al., ESWC 2016 ([arXiv 1707.08470](https://arxiv.org/pdf/1707.08470), [code](https://github.com/sujanucsc/IEL-Twitter)); follow-up **Implicit Entity Recognition, Classification and Linking in Tweets** — Hosseini et al., SIGIR 2019 ([ACM](https://dl.acm.org/doi/10.1145/3331184.3331416)) | Links entities a tweet refers to *without naming them*, using KB facts + context (e.g. a tweet naming director Linklater → `dbr:Boyhood_(film)`). 21% of movie tweets and 40% of book tweets contain implicit references. | **High.** Same core idea: an entity referred to without its name is grounded through KB facts. | Tweets, not KG extraction; ranks to a best entity rather than emitting facts about it; unclear whether it abstains; DBpedia-only, pre-LLM. **Must read in full before G1.** |
| 2 | **Do I have the Knowledge to Answer? (GrailQAbility)** — Patidar et al., ACL 2023 ([ACL](https://aclanthology.org/2023.acl-long.576.pdf)); **RetinaQA** ([arXiv 2403.10849](https://arxiv.org/pdf/2403.10849)) | KBQA benchmark with unanswerable questions caused by KB incompleteness; SOTA KBQA models drop and often flag unanswerability for the wrong reasons. Later work calls it the only public KBQA dataset with unanswerable questions. | **Medium-high.** Our "formalise + ground or abstain" step is KBQA with answerability. | Questions, not text being extracted; no anonymous-node output; Freebase-based (to check). Our "missing fact" ≈ their unanswerable-by-incompleteness. |
| 3 | **Bridging anaphora + knowledge**: Hou, *Bridging Anaphora Resolution as Question Answering*, ACL 2020 ([arXiv 2004.07898](https://arxiv.org/pdf/2004.07898)); Pandit et al., *Integrating KG embeddings … for bridging anaphora resolution*, CRAC 2020 ([ACL](https://aclanthology.org/2020.crac-1.7/)) | Resolves descriptions linked to an antecedent by a relation ("the husband" → Marie Antoinette). KG used as embeddings / commonsense (WordNet, TEMPROB), not as a queried KB. | **Medium.** Detection of relational descriptions is exactly bridging. | They resolve to the **antecedent mention**; we resolve to the **unnamed entity's identity** in a KB and emit facts. Search found no system linking bridging anaphors to Wikidata — weak evidence, to confirm. |
| 4 | **Extract, Define, Canonicalize (EDC)** — Zhang & Soh, EMNLP 2024 ([ACL](https://aclanthology.org/2024.emnlp-main.548/), [code](https://github.com/clear-nus/edc)) | LLM KG construction: open extraction → schema definition → canonicalisation; works with or without a target schema; handles large schemas. | **Medium** on the ontology-agnostic angle. | Schema adaptation for relations, not grounding unnamed entities; no KB-uniqueness abstention. |
| 5 | **Learn to Not Link: NIL prediction in entity linking** — ACL Findings 2023 ([ACL](https://aclanthology.org/2023.findings-acl.690.pdf)); ReFinED (NIL as a candidate) | Predicts when a mention has no KB entity; splits NIL into *Missing Entity* vs *Non-Entity Phrase*. | **Medium** on abstention. | Named mentions only; NIL = "not in KB", ours = "unnamed, and unique / ambiguous / unrecorded in KB". |
| 6 | **Descriptive & nominal mentions in EL**: TAC KBP EDL guidelines (nominal mentions, [PDF](https://tac.nist.gov/2015/KBP/ColdStart/guidelines/TAC_KBP_2015_EDL_Guidelines_V1.2.pdf)); Freiburg EL annotation guidelines (descriptive mentions, [GitHub](https://github.com/ad-freiburg/entity-linking-annotation-guidelines)); Babelfy, TACL 2014 ([ACL](https://aclanthology.org/Q14-1019.pdf)) | Annotate/link common-noun or descriptive mentions ("second war between Pakistan and India in 1965" → Indo-Pakistani War of 1965). | **Medium.** Descriptive mentions are our input class. | Annotation/linking of the mention; no relational KB query, no abstention, not inside triple extraction. |

## Benchmarks and resources (details in `benchmark_matrix.csv`)

- **Text2KGBench** — Mihindukulasooriya, Tiwari, Enguix, Lata, ISWC 2023 Resources Track, LNCS pp. 247–265, DOI 10.1007/978-3-031-47243-5_14 ([arXiv 2308.02357](https://arxiv.org/abs/2308.02357), [Zenodo](https://zenodo.org/records/7916716)). Defines seven metrics incl. ontology conformance and hallucination. Co-authored by our mentor Nandana.
- **Text2KGBench-LettrIA** — re-annotation of the 4,860 DBpedia-WebNLG sentences, >14,000 triples, KBC-LM/LM-KBC at ISWC 2025 ([CEUR Vol-4041](https://ceur-ws.org/Vol-4041/paper3.pdf)). Cleaner evaluation target than the original half.
- **TekGen / KELM** — Agarwal et al., NAACL 2021 ([ACL](https://aclanthology.org/2021.naacl-main.278/)).
- **REBEL** ([HF](https://huggingface.co/datasets/Babelscape/rebel-dataset)), **DocRED** — Yao et al., ACL 2019 ([ACL](https://aclanthology.org/P19-1074.pdf)), **WebNLG+ 2020** ([ACL](https://aclanthology.org/2020.webnlg-1.7/)), **AIDA-CoNLL** ([wiki](https://github.com/wikilinks/conll03_nel_eval/wiki/Data%20set)), **QALD-10** — Usbeck et al., Semantic Web journal 2024 ([SWJ](https://www.semantic-web-journal.net/content/qald-10-%E2%80%94-10th-challenge-question-answering-over-linked-data-0)), **LC-QuAD 2.0** — Dubey et al., ISWC 2019 ([GitHub](https://github.com/AskNowQA/LC-QuAD2.0)).
- **SynEL** — 2025 synthetic EL benchmark; reports micro-F1 dropping by up to 25 points on low-resource vs high-resource entities ([PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12782364/)). Supports stratifying our test set by popularity. *To read.*

## Representing unknown entities

- **Blank nodes** — Hogan, Arenas, Mallea, Polleres, *Everything you always wanted to know about blank nodes*, J. Web Semantics 27–28 (2014) 42–69, DOI 10.1016/j.websem.2014.06.004 ([PDF](https://marceloarenas.cl/publications/jws14.pdf)). Blank nodes as existential variables; entailment/leanness complexity.
- **Skolemisation** — Hogan, *Skolemising Blank Nodes while Preserving Isomorphism*, WWW 2015 ([ACM](https://dl.acm.org/doi/10.1145/2736277.2741653)).
- **Wikidata "unknown value"** — the Wikibase data model's *PropertySomeValueSnak* = "a value that exists but whose identity or value is unknown" (vs *NoValueSnak*). WDQS replaced blank nodes with skolem IRIs under `/.well-known/genid/` because blank nodes can't be used in its update patches ([RDF dump format](https://www.mediawiki.org/wiki/Wikibase/Indexing/RDF_Dump_Format), [skolemisation](https://www.mediawiki.org/wiki/Wikidata_Query_Service/Blank_Node_Skolemization), [T244341](https://phabricator.wikimedia.org/T244341)). **Directly relevant to our representation choice** — a native precedent, and an argument for skolem IRIs over plain blank nodes in an updatable dataset. We measured it too: 1,209 enwiki-articled items carry an unknown-value spouse.

## Adjacent (lower priority)

- Anchor-constrained KG extraction with provenance tracking, MDPI Computers 15(3):178, 2025 ([MDPI](https://www.mdpi.com/2073-431X/15/3/178)) — reports entity hallucination eliminated by grounding to text spans; relation hallucination dominant. *To read.*
- *Toward a Gricean Retreat: Probing LLMs for Knowledge Boundaries and Referent Specificity* ([arXiv 2608.13484](https://arxiv.org/pdf/2608.13484)) — LLM behaviour on unknown entities. *To read.*
- MHEL-LLaMo / LLM historical EL ([arXiv 2601.08500](https://arxiv.org/pdf/2601.08500)) — separating NIL prediction from candidate selection reduces LLM bias toward always linking. *To read.*

## Missing citation

- **NEF 1.0's own paper** (accepted at KGSWC per Tsoru) — not found by search. **Ask Tsoru for the exact citation.**

## Provisional gap statement (pass 1 — not yet a claim)

Prior work grounds *unnamed* entities only in tweets (implicit EL) or resolves descriptions to *antecedent mentions* (bridging); KBQA handles description→query with answerability but on questions, not text being extracted; KG-construction work handles schema adaptation and NIL, but only for named mentions. **We found no work that, inside KG extraction, turns a relational description of an unnamed entity into a KB query, grounds it only when the answer is unique, and otherwise emits a provenance-tagged anonymous node — across ontologies.** This rests on searches, not full reads; implicit entity linking (#1) is the paper that could break it.

## Pass 2 — full reads (2026-10-16)

### Perera et al., *Implicit Entity Linking in Tweets*, ESWC 2016 (arXiv 1707.08470) — read in full

- **Task (their Def. 2):** given a tweet *known to contain* an implicit mention *of a given type* (Movie or Book), output the entity. Input is (type, text). One entity per tweet.
- **Definition of "implicit":** the name is absent, and the mention is not an alias or a coreference of a named entity in the tweet (their Def. 1). Close to our O-REL/O-DESC, but restricted to the tweet's *topic* entity.
- **Overlap with us — real.** Section 2.2 shows people refer to entities "through characteristics", e.g. "Richard Linklater movie" (director), "Ellar Coltrane's movie" (actor), "latest movie shot in Houston" (location). Several of these *are* relational descriptions.
- **Method:** an entity-model network, i.e. bags of clue phrases per entity.
  - Facts: rdfs:labels of neighbours over the top-m DBpedia relations, plus rdfs:comment.
  - Context: 1,000 recent tweets per entity.
  - Temporal salience: 30-day Wikipedia page views.
  - Ranking: clue-overlap candidate selection (top-25), then SVMrank on cosine similarity + salience.
- **KB use is lexical:** DBpedia neighbours become words to match. Relations are never used as constraints, and nothing is queried at link time.
- **Data and results:**
  - Prevalence on keyword-filtered tweets: 21% of movie mentions and 40% of book mentions are implicit. Our 2.7% in encyclopedic text is a different genre, not a contradiction.
  - Evaluation set: 397 implicit tweets; candidate recall ~90–95%; top-1 accuracy ~61% in both domains.
  - Contextual tweets add +15–18 points, i.e. what carries them is *popularity and recency*, not KB structure.
  - Error types: thin context, entity not yet in the KB, cold start, two implicit entities per tweet.
- **No abstention.** Every candidate set yields a top-1. NIL handling is listed as future work, and there is no notion of "the KB answer is not unique".
- **What it does not do:** extract facts, emit triples or anonymous nodes, work without a known target type, or handle long-tail entities (salience favours popular ones).

### Hosseini (with Bagheri), implicit entity recognition and linking in tweets — SIGIR 2019 (1 page, p. 1448 — likely a doctoral-consortium abstract; not seen), Applied Ontology 2019, IP&M 2022, PhD thesis Ryerson 2022 — thesis read for problem setup, method and limits

- **Dataset:** 7,870 tweets labelled explicit / implicit / neither. ~15% of tweets carry an implicit entity.
- **Linking:**
  - (a) Ad-hoc retrieval of Wikipedia descriptions, with the tweet as the query.
  - (b) Learning-to-rank over KG features. Metrics: P@1, MRR.
- **Candidate selection is the closest technical step to ours:** link the tweet's explicit entities, then take every DBpedia neighbour of the wanted type.
  - We do the same anchor-plus-KB-neighbourhood lookup, but *constrained by the specific relation*, and we decide by answer cardinality instead of ranking.
- **Stated assumptions:**
  - The domain/type of the implicit entity is known in advance.
  - The tweet *does* contain exactly one implicit entity.
  - The thesis calls both limitations and lists open-domain linking, long-tail entities, and entities absent from the KG as future work.
- **No abstention or anonymous-node output.** Ranking always returns a top-1.

### OpenEL — Cui, Rolston, Walker, Hockey, LREC 2022 (dialogue entity linking to Wikidata) — read for definitions and NIL policy

- Annotates definite referring expressions and anaphora (he/she/it/they) in 179 dialogues and links them to Wikidata. Best system: Flair+BLINK, F1 0.65.
- Its "definite expressions" are mostly names or name-like phrases ("my Giants", "the forest planet"), not relational descriptions.
- **Useful for our motivation.** Annotators met referents with *no* Wikidata ID or *no unique* ID (a specific "Yankees vs Red Sox game" when Wikidata only has the season). Their policy was to **drop them** ("ignoring uncertain mentions or unlinkable entities"). That is exactly the case our anonymous node keeps.

### Searches since 2023 (pass 2)

- No 2023–2026 paper found that:
  - (i) compiles a relational description of an unnamed entity into a KB query inside text-to-KG extraction,
  - (ii) grounds it only on a unique answer, and
  - (iii) otherwise emits a provenance-tagged anonymous node.
- Nearby work:
  - LLM-KG hallucination benchmarks (KGHaluBench 2026, KG-Guard 2026, MultiHal 2025) measure abstention in QA, not extraction.
  - KBQA systems such as ChatKBQA accept the first executable query, with no answer-cardinality check.
  - An ontology-compliant extraction pipeline (arXiv 2609.17291) mints new IDs for unmatched entities by fuzzy matching. That is the closest to an "anonymous node", but it does no relational grounding.
- These are search-level results, not full reads.

### Updated positioning (after pass 2)

| | Implicit EL (Perera; Hosseini) | Ours |
|---|---|---|
| Text | Tweets, keyword-filtered | Encyclopedic or open text, inside KG extraction |
| Which unnamed entity | The tweet's topic, one per tweet, type given | Any non-topic entity, several per sentence, type inferred from relation and ontology |
| KB use | Neighbour labels as bag-of-words clues; ranking | Relation-constrained query; answer cardinality decides |
| Output | Top-1 entity, always | Entity if unique; else an anonymous node with candidates, or a missing-fact tag |
| Popularity | Relies on salience and recent tweets | Built for the long tail; stratified by popularity |
| KB | DBpedia only | Ontology-agnostic adapters (DBpedia, Wikidata, …) |

**The gap statement survives pass 2 for implicit EL.** We must cite implicit EL as the origin of "entities referred to through their characteristics". Our novelty claim rests on four things:
- relation-constrained grounding,
- abstention by cardinality,
- anonymous-node output inside extraction,
- cross-ontology adapters.

A fair baseline is "implicit-EL style": link the anchor, take KB neighbours of the inferred type, rank, and always pick top-1. It shows what abstention buys.

## Pass 2 — still to read, in this order

1. ~~Perera et al. 2016 + Hosseini (implicit EL)~~ — done above.
2. Patidar et al. 2023 (GrailQAbility) + RetinaQA.
3. Hou 2020; Pandit et al. 2020.
4. EDC (Zhang & Soh 2024).
5. Learn to Not Link (2023).
6. Text2KGBench + Text2KGBench-LettrIA (evaluation protocol, hallucination metrics).
7. Snowball: who cites implicit EL and GrailQAbility since 2023.
