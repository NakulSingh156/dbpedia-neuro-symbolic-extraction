"""Word version of METHODOLOGY.md for Tsoru -> ~/Desktop/GSoC 2026/DBpedia/Tsoru_Architecture_Methodology.docx
Styles are taken from Nakul's earlier meeting doc (Meeting_Anonymous_Nodes_Paper.docx)."""
import copy, os
import docx
from docx.shared import Pt, Cm, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

BASE = os.path.expanduser("~/Desktop/GSoC 2026/DBpedia")
d = docx.Document(os.path.join(BASE, "Meeting_Anonymous_Nodes_Paper.docx"))
body = d.element.body
for el in list(body):
    if el.tag != qn("w:sectPr"):
        body.remove(el)

def para(text="", bold_lead=None, size=None, style=None, italic=False, space_after=4):
    p = d.add_paragraph(style=style)
    if bold_lead:
        r = p.add_run(bold_lead); r.bold = True
        if size: r.font.size = Pt(size)
    r = p.add_run(text); r.italic = italic
    if size: r.font.size = Pt(size)
    p.paragraph_format.space_after = Pt(space_after)
    return p

def h1(t, new_page=False):
    p = d.add_paragraph(t, style="Heading 1")
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.page_break_before = new_page

def bullets(items, numbered=False):
    for it in items:
        st = "List Number" if numbered and "List Number" in [s.name for s in d.styles] else "List Bullet" if "List Bullet" in [s.name for s in d.styles] else "List Paragraph"
        p = d.add_paragraph(style=st)
        if isinstance(it, tuple):
            r = p.add_run(it[0]); r.bold = True; p.add_run(it[1])
        else:
            p.add_run(it)
        p.paragraph_format.space_after = Pt(2)

def shade(cell, hexcol):
    tcPr = cell._tc.get_or_add_tcPr(); s = OxmlElement("w:shd")
    s.set(qn("w:val"), "clear"); s.set(qn("w:color"), "auto"); s.set(qn("w:fill"), hexcol); tcPr.append(s)

def borders(table):
    tblPr = table._tbl.tblPr; b = OxmlElement("w:tblBorders")
    for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
        x = OxmlElement(f"w:{e}"); x.set(qn("w:val"), "single"); x.set(qn("w:sz"), "4"); x.set(qn("w:color"), "BFBFBF"); b.append(x)
    tblPr.append(b)

def table(rows, widths, size=9):
    t = d.add_table(rows=len(rows), cols=len(rows[0])); borders(t)
    grid = t._tbl.tblGrid
    for i, gc in enumerate(grid.findall(qn("w:gridCol"))):
        gc.set(qn("w:w"), str(int(widths[i] * 567)))
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j); c.width = Cm(widths[j]); c.text = ""
            p = c.paragraphs[0]; r = p.add_run(val); r.font.size = Pt(size)
            p.paragraph_format.space_after = Pt(0)
            if i == 0: r.bold = True; shade(c, "EDEDED")
    d.add_paragraph().paragraph_format.space_after = Pt(2)
    return t

# Title block (as in the earlier meeting doc)
p = d.add_paragraph(); r = p.add_run("Anonymous-Node Grounding: Architecture & Methodology"); r.bold = True; r.font.size = Pt(20)
p = d.add_paragraph(); r = p.add_run("How we name the entities a sentence never names, and how we'll prove it works. Draft for discussion · Nakul Singh · 16 Oct 2026"); r.font.size = Pt(11.5)

h1("1. The idea in one paragraph")
para("“His namesake nephew was a notable architect.” The nephew is never named. Today NEF drops the fact and an LLM guesses a name. "
     "We turn the description into a knowledge-base query and name the entity only when the KB returns exactly one answer. "
     "Otherwise we keep the fact with an anonymous node: carrying the candidates when the KB is ambiguous, or flagged as a missing fact when the KB records nothing. "
     "The same machinery works on any ontology through thin adapters; we show it on Wikidata and DBpedia.")
para("Scope: entities described through a relation to another entity (“her husband”, “the band’s drummer”, “the founder of Mérida”). "
     "Mentions of the text’s own subject (“He…”, “The film…”) are coreference, already handled by NEF, and are out of scope.", italic=False)

h1("2. What the evidence says (9–16 Oct)")
para("Feasible on Wikidata, safe when the KB answers, new against the closest prior work. The case is sparse in abstracts, so the test set has to be built on purpose.")
table([
 ["Finding", "What it forces in the design"],
 ["43% of abstract sentences have an unnamed reference, but 40% are the topic itself", "Scope = non-topic entities only"],
 ["Relational descriptions of other entities: 2.7% of sentences (95% CI 1.4–5.2%); KB-groundable ≈ 0.2–1%", "Build the test set deliberately; widen the text source beyond abstracts"],
 ["Relations are mostly unique once nested places are merged: Wikidata 87%, DBpedia 77%", "“Ground only if unique” is a workable rule"],
 ["Same 2,271 facts: Wikidata grounds 47–49%, DBpedia 19–21%", "Wikidata = primary KB; missing facts are an outcome, not an error"],
 ["When the KB answers, it agrees with the text ≈ 96% (Wikidata) / 98% (DBpedia) after place-in-place and modelling conventions; raw exact-ID agreement looked like 58% / 84%", "Answer comparison must understand conventions: nationality vs country, historical states, broader vs narrower classes, player vs sport"],
 ["Father/mother 99.6% unique vs “parent” 51%; team and child are many-valued", "Decompose descriptions with constraints: husband = spouse + male; eldest son = child + male + ordinal"],
 ["Real cases are often nested: “the grandson of the founder of Mérida”", "Internal representation = a path of relations; an anchor can itself be a description"],
 ["Implicit entity linking (Perera et al., ESWC 2016; Hosseini & Bagheri 2019–22): links the unnamed topic of a tweet by ranking; type given in advance; always answers; never abstains", "Our novelty: relation-constrained grounding + abstention by answer count + anonymous nodes inside extraction + cross-ontology adapters. Their ranker becomes a baseline"],
 ["OpenEL (LREC 2022) annotators dropped referents with no unique Wikidata ID", "Motivation: we keep what others discard"],
], [8.2, 9.3])
para("Occurrence labels are a first pass by Claude; Nakul’s blind 50-sentence check (Cohen’s κ) is in progress before any rate is cited.", italic=True, size=9)

h1("3. Architecture", new_page=True)
d.add_picture(os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures", "architecture.png"), width=Cm(17.3))
table([
 ["Step", "What it does", "Reuses from NEF 2.0"],
 ["M1 Detect & parse", "Finds unnamed non-topic mentions; fills a structured description (anchor, relation chain, gender/ordinal/time constraints). LLM with structured output + a high-recall pattern scanner", "Node 1"],
 ["M2 Resolve anchor", "Links the anchor: the topic, a named entity, or (nested) another description resolved first", "Nodes 2–3, surface-form index, coref tiers"],
 ["M3 Map relations", "Phrase → property path + direction, via the adapter’s relation lexicon (nephew = sibling → child + male), retrieval and LLM re-rank; low confidence → unresolved", "Node 3 predicate linker"],
 ["M4 Compile query", "The KB-neutral description → the KB’s SPARQL dialect (Wikidata qualifiers when ordinals or time matter)", "—"],
 ["M5 Execute & normalise", "Runs it; merges answers that are really the same (place-in-place, conventions, sameAs); filters by type and gender", "containment logic from the surveys"],
 ["M6 Decide", "1 answer → grounded · 2+ → anonymous node + candidates · 0 → missing fact · not mappable → unresolved", "SPARQL gate"],
 ["M7 Emit", "Triples with provenance through the adapter’s writer", "output harness"],
], [3.3, 10.6, 3.6])
para("Adapters are the only KB-specific code: OntologyAdapter (properties, relation lexicon, containment, conventions) · EntityIndex · KBQuery · OutputWriter. "
     "The DBpedia adapter is a pure refactor of NEF 2.0 and must reproduce v14 within ±0.02 before anything else is built. "
     "Wikidata is the primary adapter; YAGO 4.5 (schema.org classes) is an optional third to show generality.", bold_lead="Adapters. ")
para("Skolem IRIs rather than plain blank nodes (stable across updates; Wikidata itself switched to them). Each anonymous node carries its type, the description text, its anchor and path, a status (ambiguous / missing fact / unresolved) and candidates. "
     "Provenance via RDF-star or named graphs; the Wikidata writer uses Wikidata’s native “unknown value”.", bold_lead="Output. ")

h1("4. Worked example")
para("“Marie Antoinette’s husband was guillotined in 1793.” Anchor Q47365, relation spouse (P26) + male. "
     "Wikidata returns two spouses, Louis XVI and Axel von Fersen the Younger, so the output is an anonymous node with two candidates. "
     "An LLM answers “Louis XVI”, which is right here, but the KB as published does not license it. That difference is what the paper measures.")

h1("5. Approaches compared")
para("The same LLM runs inside every system that uses one, so the comparison isolates the method, not the model.")
table([
 ["ID", "System", "KB use", "Abstains?"],
 ["B0", "NEF 2.0 as-is (STRICT)", "named entities only", "drops the fact"],
 ["B1", "LLM, closed book", "none", "only if told it may"],
 ["B2", "Implicit-EL ranker (Perera / Hosseini style)", "anchor + KB neighbours, ranked", "no, always top-1"],
 ["B3", "LLM + KB tool (LLM writes SPARQL)", "LLM-written query", "if the LLM chooses"],
 ["B4", "LLM + retrieved KB facts (RAG)", "anchor’s facts as context", "if the LLM chooses"],
 ["N", "Ours, neuro-symbolic", "compiled query + answer-count rule", "by construction"],
 ["H", "Ours, hybrid", "N; B3’s query when relation mapping is unsure", "by construction"],
], [1.2, 6.3, 6.2, 3.8])
para("Local: Qwen2.5-7B, Llama-3.1-8B (GPU permitting). API: GPT-4o, GPT-5.6 Luna, Claude, budget-capped and only with your OK before any spend.", size=9.5)

h1("6. Experiments")
table([
 ["RQ", "Question", "Experiment"],
 ["RQ1", "How often can an unnamed entity be grounded uniquely; how does it depend on KB and relation?", "Groundability survey (done on Phase-1 facts for both KBs; repeated on test items, by relation family)"],
 ["RQ2", "Does KB-constrained grounding with abstention beat the LLM and KB-tool baselines, especially on the long tail and when nothing is recorded?", "All systems on the controlled set and the natural set, split by KB × answer type × popularity; ablations"],
 ["RQ3", "Can one architecture serve different ontologies, and at what cost?", "Adapter generality (DBpedia regression, Wikidata, optional YAGO): code/config per adapter, core changes (target 0); cost per 1,000 sentences"],
], [1.3, 8.0, 8.2])
para("no containment merging · no convention rules · no gender/ordinal constraints · no abstention · forward-only paths · no nested recursion · LLM-written query only.", bold_lead="Ablations (dev only): ")
para("every wrong output goes into one bucket (detection miss, wrong anchor, wrong property, KB gap, genuine ambiguity, convention mismatch, extraction noise), plus 5–6 case studies including one where the LLM beats us.", bold_lead="Error analysis: ")

h1("7. Test set")
bullets([
 ("Controlled set (power): ", "built from KB facts, rewritten so the target is described instead of named. The KB decides the gold: unique → entity, several → candidate set, none → abstain. 2 KBs × 3 answer types × 3 popularity tiers ≈ 900 items (±7 pts per cell), plus ~100 nested items. Templates → LLM paraphrase → every item checked by a person."),
 ("Natural set (realism): ", "mined from Wikipedia abstracts and full article bodies (biographies first) with the scanner + an LLM detector; every hit verified by hand; 200–300 items with gold on both KBs."),
 ("No-harm check: ", "Text2KGBench wikidata_tekgen end-to-end F1 must not drop with the module on. Your CoNLL / Wikidata benchmarks added once we pin which ones."),
 ("Quality: ", "written guidelines; 15% double-annotated (Cohen’s κ); frozen and hashed before any tuning; 20% dev."),
])

h1("8. Metrics")
table([
 ["Gold answer", "Correct behaviour", "Measured as"],
 ["unique", "name the gold entity", "grounding accuracy · wrong-ID rate · over-abstention"],
 ["ambiguous", "anonymous node + candidates", "candidate recall and set size · false-grounding rate"],
 ["none in KB", "anonymous node + missing fact", "abstention precision / recall"],
], [3.0, 6.0, 8.5])
para("hallucinated-identity rate (names an entity the evidence doesn’t license); grounding F1; a risk–coverage curve (accuracy vs share answered) so hard abstention and LLM confidence are compared fairly; end-to-end triple F1 on the natural set; $ per 1,000 sentences. "
     "3 runs per LLM system, bootstrap 95% CIs, paired McNemar tests; KB snapshots pinned and every query cached.", bold_lead="Headline: ")

h1("9. Plan and gates")
table([
 ["Phase", "Dates", "Output", "Gate / status"],
 ["1 Scope & novelty", "15 Oct – 8 Nov", "related work, benchmarks, contribution", "G1 · implicit EL read in full; KBQA-answerability and bridging next"],
 ["2 Feasibility", "9 – 29 Nov", "Wikidata survey, occurrence, conventions", "G2 · mostly done: Wikidata ≥ 30% ✔; occurrence 2.7% vs 3% bar → borderline"],
 ["3 Test set", "30 Nov – 10 Jan", "controlled ~900 + natural 200–300, κ", "G3 freeze"],
 ["4 Baselines", "11 – 31 Jan", "B0–B4, stratified, with cost", "G4 headroom"],
 ["5 Adapters", "14 Dec – 31 Jan", "DBpedia refactor, Wikidata adapter, writer", "G5 regression (v14 ± 0.02)"],
 ["6 Approaches", "1 Feb – 7 Mar", "N, H, ablations on dev", "—"],
 ["7 Evaluation", "8 Mar – 4 Apr", "all tables with CIs, errors, cost", "G6 every claim has a CI"],
 ["8 Writing", "22 Mar – ISWC deadline (~early May)", "paper + code and data release", "submit"],
], [3.2, 3.6, 5.2, 5.5])
para("ISWC research track → ISWC Resources track (test set + framework) → KGSWC / ESWC workshop → workshop paper on NEF 2.0 results. Nothing from Phases 1–4 is wasted under any of them.", bold_lead="Fallbacks: ")

h1("10. Decisions we need from you")
for i, q in enumerate([
 "Scope: non-topic relational descriptions only, with topic coreference out. Agree?",
 "Primary KB = Wikidata, DBpedia second, YAGO 4.5 as an optional third?",
 "Representation: skolem IRIs + RDF-star provenance, Wikidata “unknown value” in the Wikidata writer?",
 "Natural-text source: abstracts + full article bodies, biographies first?",
 "Which CoNLL / Wikidata benchmarks you meant, so we can adapt them.",
 "API budget for the LLM baselines (B1, B3, B4).",
 "Feasibility gate: occurrence is 2.7% vs our 3% bar. Accept with the wider text source and a controlled-set-led evaluation?",
], 1):
    p = d.add_paragraph(style="List Paragraph"); r = p.add_run(f"{i}. "); r.bold = True; p.add_run(q)
    p.paragraph_format.space_after = Pt(2)

out = os.path.join(BASE, "Tsoru_Architecture_Methodology.docx")
d.save(out); print("saved", out)
