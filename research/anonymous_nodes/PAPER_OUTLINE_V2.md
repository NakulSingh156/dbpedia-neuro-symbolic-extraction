# Paper outline v2 — after Tsoru's November meeting (20 Nov 2026)

Supersedes the grounding-first framing of `contribution.md` v0. Under discussion with Tsoru; ISWC research track is the target.

**Working title:** *Don't Drop the Unnamed: Anonymous-Node Generation for Text-to-Knowledge-Graph Extraction*

## 1. Problem

Text states facts about people and things it never names:
- "Another younger brother died in infancy."
- "The portrait was painted by an unknown artist."
- "She ran a catering business with her husband."

Today's extractors handle these badly. On our 100-sentence pool, an LLM asked to extract triples turned **75 of 100** unnamed entities into junk nodes ("unknown father", "brother_of_X") and dropped 16. In October the rate was 70–74% junk or lost. Named-entity pipelines (NEF 2.0 STRICT) drop the facts outright.

## 2. Task

**Input:** a text plus a reference KB (a frozen evidence slice).

**Output:** a KG in which every described entity is one of:
- **named** — when text or KB evidence supports exactly one identity, with a grounding tier: schema-unique / data-unique;
- an **anonymous node** with a status, its description, anchor and relation path, and **provenance**. The status is one of:
  - *ambiguous*, with a candidate list;
  - *missing*, when the KB has no fitting value;
  - *text-unknown*, when the text says the identity is unknown;
  - *unresolved*, when the anchor or relation can't be mapped.

**Requirement:** never invent an identity, never drop the fact.

## 3. Contributions

1. **Task and representation.**
   - Anonymous-node generation as a first-class output of text-to-KG extraction.
   - Skolem-IRI anonymous nodes with status, candidates and provenance, aligned with Wikidata's "unknown value" (somevalue).
   - Two phenomena distinguished: relational descriptions (R) and stated-unknown identities (U).
2. **Benchmark.**
   - Manually annotated, stratified by outcome type and popularity.
   - Frozen, hashed KB evidence; split by article; second annotator plus κ.
   - Text2KGBench used as a no-harm check.
3. **Method.** Neuro-symbolic: detect the description, resolve the anchor safely, map relation paths through a lexicon or ontology adapter, query the KB, then decide using:
   - the answer count;
   - schema-unique vs data-unique tier;
   - convention-aware comparison;
   - the text-unknown rule;
   - pronoun-anchor safety.

   It runs on Wikidata and DBpedia through adapters.
4. **Empirical study.**
   - Baselines: LLM extraction, LLM writing SPARQL (KBQA inside extraction), implicit-EL ranker, RAG.
   - Several models, local and API, with cost.
   - Ablations of each decision rule.
5. **Analyses:**
   - groundability on two KBs: Wikidata grounds 2.3× more than DBpedia; ≈96% agreement once conventions are handled;
   - how often the phenomenon occurs;
   - failure modes: anchor errors (≈14% of raw candidates), KB–text conflicts, and "Wikipedia names what Wikidata knows".

## 4. Research questions

| RQ | Question | Evidence planned |
|---|---|---|
| RQ1 | How often do texts mention unnamed entities, of which kinds, and how often can a KB name them? | Occurrence study; groundability on Wikidata vs DBpedia; benchmark statistics |
| RQ2 | Can a system keep these facts without inventing identities, and how do LLM-only and LLM+KB baselines compare? | Main table: facts kept, junk-node rate, wrong-identity rate, candidate recall, status accuracy |
| RQ3 | Does it work across KBs and models, without harming ordinary extraction, at what cost? | Adapters (WD/DBpedia); models (Llama, Qwen, Luna, …); Text2KGBench no-harm; $ per 1k sentences |

## 5. Experiments

1. **Main comparison** on the frozen test split, by phenomenon (R/U), outcome type and popularity tier. Systems:
   - ours;
   - LLM extraction;
   - LLM+SPARQL;
   - implicit-EL ranker;
   - RAG.
2. **Model sweep:** local 7–8B models, then cheap API models (Luna), then stronger models only if needed.
3. **Ablations:**
   - no text-unknown rule;
   - no anchor safety;
   - no schema tier;
   - no convention-aware comparison;
   - no "another/unnamed" exclusion;
   - whole-article vs paragraph input.
4. **No-harm:** firing rate and correctness on ordinary Text2KGBench sentences, then end-to-end triple F1 with the module on.
5. **Error taxonomy and case studies,** including a case where an LLM beats the KB (a famous entity whose fact is missing from the KB).

## 6. Related work positioning

| Line | What it does | Difference |
|---|---|---|
| Implicit entity linking (Perera et al. 2016; Hosseini & Bagheri 2019–22) | Links the unnamed *topic* of a tweet; always answers | We extract facts, keep anonymous nodes, abstain by evidence |
| KBQA answerability (GrailQAbility 2023; RetinaQA 2024) | Detects unanswerable *questions* | Answers are sets (no "ambiguous" outcome); no extraction; no anonymous-node output |
| NIL prediction (Learn to Not Link 2023) | Named mentions without a KB entry | Ours are unnamed mentions of real entities |
| Non-named entities (Paris & Suchanek 2021; Ezzabady & Benamara, GenAIK 2025) | Concept noun phrases in triple extraction | Not unnamed real-world entities; no identity decision |
| Wikidata somevalue / skolem IRIs | Native "unknown value" representation | We *generate* such nodes from text, with status and candidates |
| Wikidata-aligned text-to-KG (Wikontic, AAAI-26; KGGen 2025) | Schema-aligned extraction | Possible baselines; no unnamed-entity handling |

## 7. Threats and how we address them

- **"It's just KBQA."** The LLM+SPARQL baseline answers this directly; the anonymous-node output and the ambiguous / text-unknown outcomes are not KBQA.
- **"The phenomenon is rare."** Use occurrence numbers per source. The U type is common in biographies and historical text. Keeping facts matters at KG scale.
- **Benchmark circularity** (Wikipedia names what Wikidata knows). Use paragraph-level input as the main setting, add other text sources, and keep a controlled slice for the KB-unique and ambiguous cells.
- **Single-annotator labels.** Second annotator, κ, adjudication.
