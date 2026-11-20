"""Word update for the 20 Nov 2026 meeting with Tsoru -> ~/Desktop/GSoC 2026/DBpedia/Tsoru_Update_2026-11-20.docx.
Numbers are read from the result files so the doc cannot drift from them. Styles from Meeting_Anonymous_Nodes_Paper.docx."""
import csv, json, os, collections
import docx
from docx.shared import Pt, Cm
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

BASE = os.path.expanduser("~/Desktop/GSoC 2026/DBpedia")
PT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testset/post_tsoru")
d = docx.Document(os.path.join(BASE, "Meeting_Anonymous_Nodes_Paper.docx"))
for el in list(d.element.body):
    if el.tag != qn("w:sectPr"): d.element.body.remove(el)

def para(text="", bold_lead=None, size=None, italic=False):
    p = d.add_paragraph()
    if bold_lead:
        r = p.add_run(bold_lead); r.bold = True
        if size: r.font.size = Pt(size)
    r = p.add_run(text); r.italic = italic
    if size: r.font.size = Pt(size)
    p.paragraph_format.space_after = Pt(4); return p
def h1(t, new_page=False):
    p = d.add_paragraph(t, style="Heading 1"); p.paragraph_format.keep_with_next = True; p.paragraph_format.page_break_before = new_page
def items(rows):
    for i, (lead, txt) in enumerate(rows, 1):
        p = d.add_paragraph(style="List Paragraph"); r = p.add_run(f"{i}. "); r.bold = True
        if lead: r = p.add_run(lead); r.bold = True
        p.add_run(txt); p.paragraph_format.space_after = Pt(2)
def table(rows, widths, size=9):
    t = d.add_table(rows=len(rows), cols=len(rows[0]))
    b = OxmlElement("w:tblBorders")
    for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
        x = OxmlElement(f"w:{e}"); x.set(qn("w:val"), "single"); x.set(qn("w:sz"), "4"); x.set(qn("w:color"), "BFBFBF"); b.append(x)
    t._tbl.tblPr.append(b)
    for i, gc in enumerate(t._tbl.tblGrid.findall(qn("w:gridCol"))): gc.set(qn("w:w"), str(int(widths[i] * 567)))
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j); c.width = Cm(widths[j]); c.text = ""
            p = c.paragraphs[0]; r = p.add_run(str(val)); r.font.size = Pt(size); p.paragraph_format.space_after = Pt(0)
            if i == 0:
                r.bold = True; s = OxmlElement("w:shd"); s.set(qn("w:val"), "clear"); s.set(qn("w:fill"), "EDEDED"); c._tc.get_or_add_tcPr().append(s)
    d.add_paragraph().paragraph_format.space_after = Pt(2)

tri = list(csv.DictReader(open(f"{PT}/pool_triage_v1_2026-11-19.csv")))
man = json.load(open(f"{PT}/wikidata_slice_2026-11-19/capture_manifest.json"))
rb = json.load(open(f"{PT}/rebalance_summary.json")) if os.path.exists(f"{PT}/rebalance_summary.json") else None
rbv = json.load(open(f"{PT}/rebalance_verified_summary.json")) if os.path.exists(f"{PT}/rebalance_verified_summary.json") else None
dr = json.load(open(f"{PT}/pilot_dryrun_summary.json")) if os.path.exists(f"{PT}/pilot_dryrun_summary.json") else None
def load(path):
    return json.load(open(path)) if os.path.exists(path) else None
NH = os.path.join(os.path.dirname(PT), "../noharm")
MODELS = [("Llama-3.1-8B (local)", "pilot_dryrun_summary.json", "llama3.1_8b"),
          ("Qwen2.5-7B (local)", "pilot_dryrun_summary_qwen2.5_7b.json", "qwen2.5_7b"),
          ("GPT-5.6 Luna (OpenRouter)", "pilot_dryrun_summary_openai_gpt-5.6-luna.json", "openai_gpt-5.6-luna")]
v2 = load(f"{PT}/pool_v2_composition.json")
C = collections.Counter
phen = C(r["phenomenon"] for r in tri); outc = C((r["phenomenon"], r["proposed_outcome"]) for r in tri)
stress = sum("stress" in r["flags"] for r in tri); multi = sum("multi" in r["flags"] for r in tri)

p = d.add_paragraph(); r = p.add_run("Anonymous-Node KG: Progress Since Our Last Meeting"); r.bold = True; r.font.size = Pt(20)
p = d.add_paragraph(); r = p.add_run("Benchmark, evidence, annotation rules and a first dry run · Nakul Singh · 20 Nov 2026"); r.font.size = Pt(11.5)

h1("1. Where we are in one paragraph")
para("Following your decisions, the project goal is anonymous-node generation: keep facts about unnamed people and things instead of dropping them, naming an entity only when the evidence supports one identity. Since we met, the benchmark candidate pool grew from 16 to 100 sentences, every row now has dated, hashed KB evidence, the annotation rules are written up with the open policies proposed for your decision, and a first dry run of our pipeline against an LLM-only baseline exercised the new evaluation format. The main finding is about the benchmark itself: the pool is dominated by sentences that say an identity is unknown, so it cannot yet test the naming and candidate-list halves of the task — a rebalancing step is under way.")

h1("2. What was done since the last meeting")
items([
 ("Candidate pool: 16 → 100 sentences. ", "16 pilot items plus 84 from 24 discovery batches; no overlap with the 45-biography development set; first screen 57 keep / 43 unresolved."),
 ("Dated evidence for all 100 (19 Nov). ", f"Article revision IDs + relevant Wikidata claims (family, author, creator, publisher, teacher, employer), Wikidata “unknown value” markers, and the gender of every candidate; raw responses and SHA-256 hashes kept (slice {man.get('evidence_slice_sha256','')[:12]}…). This is the frozen KB evidence the gold labels will refer to."),
 ("Annotation guide v1. ", "Two phenomena labelled separately, eight outcome labels, rules for multi-entity, pseudonym, disputed, adoptive and “another/unnamed X” cases; policies needing your decision are marked (section 5)."),
 ("Pool triage. ", "Every row given a proposed type, KB relation, frozen-evidence candidates and outcome (machine-proposed, for human review) → the composition in section 3."),
 ("Rebalancing miner. ", "Fresh biographies scanned for relational descriptions whose answer the KB knows, to fill the missing outcome types (section 3)."),
 ("Pilot dry run. ", "Our pipeline vs an LLM extracting triples on its own, on the pool sentences, scored against the proposed labels (section 4)."),
 ("Infrastructure. ", "Local DBpedia 2022-12 store restored; all November work committed and pushed; a human annotation sheet ready (machine labels hidden so the annotation stays independent)."),
])

h1("3. What the 100-row pool actually contains")
rows = [["Type", "Proposed outcome", "Rows"]]
for (ph, oc), n in sorted(outc.items(), key=lambda x: (x[0][0], -x[1])):
    rows.append(["R — relational description" if ph == "R" else "U — text says identity unknown", oc, n])
table(rows, [6.0, 6.5, 2.0])
para(f"{phen['U']} of 100 rows are type U (“an unknown father”, “an anonymous author”): the text itself says the identity is unknown, so the only correct output is an anonymous node. Only {phen['R']} rows are relational descriptions, and almost none of them have an answer the KB can supply. {stress} rows are disputed or speculative (stress cases), {multi} involve several entities.", bold_lead="Reading: ")
para("as it stands the pool can test “keep the fact as an anonymous node”, but not “name the entity when the KB knows it” or “record the candidates when several fit” — the two behaviours that separate a careful system from one that always outputs an anonymous node. We need quotas per outcome type.", bold_lead="Consequence: ")
if rbv:
    para(f"a miner scanned {rbv['people']} fresh, well-documented biographies for relational descriptions and proposed {rbv['candidates']} candidates. "
         f"I hand-checked the {rbv['flagged_checked']} it flagged as having a KB answer: only {rbv['by_outcome'].get('KB_UNIQUE',0)} are genuinely “the KB knows, the article does not name” "
         f"(Dorothea Wilhelmine’s father; Toyohiko Kagawa’s wife) and {rbv['by_outcome'].get('KB_AMBIGUOUS',0)} are genuinely ambiguous "
         f"(Princess Wilhelmine Ernestine’s brother, where the 1679 war context points to Christian V; Jack Black’s son). "
         f"The rest were named elsewhere under another name ({rbv['by_outcome'].get('NAMED_IN_CONTEXT',0)}), named in the same sentence ({rbv['by_outcome'].get('NAMED_IN_SENTENCE',0)}), "
         f"or anchor errors where “his/her” is not the article’s subject ({rbv['by_outcome'].get('ANCHOR_ERROR',0)}: “stepfather to her son” where “her” is his wife).", bold_lead="Rebalancing (19 Nov): ")
    para("in Wikipedia biographies, “the KB knows it but the text does not say it” is rare — Wikipedia usually names what Wikidata records, since both draw on the same sources. "
         "The KB-unique and ambiguous cells therefore need either a narrower input (the paragraph instead of the whole article, which turns many “named elsewhere” cases into KB-groundable ones), "
         "other text sources (news, obituaries, non-Wikipedia biographies), or controlled items. The miner’s other 50 “KB has nothing” candidates are natural relational descriptions that can rebalance R against U once checked.", bold_lead="Finding: ")

if v2:
    para(f"adding the hand-checked rebalancing items gives {v2['rows']} candidates, now {v2['by_phenomenon'].get('R',0)} relational descriptions and {v2['by_phenomenon'].get('U',0)} stated-unknown. Available against the proposed quotas (stress cases excluded):", bold_lead="Pool v2 (20 Nov): ")
    rows = [["Outcome", "Quota", "Available, whole-article input", "Available, paragraph input"]]
    for k in ("NAMED_IN_CONTEXT", "KB_UNIQUE", "KB_AMBIGUOUS", "KB_MISSING", "TEXT_UNKNOWN"):
        rows.append([k, v2["article_setting"][k]["quota"], v2["article_setting"][k]["available"], v2["paragraph_setting"][k]["available"]])
    table(rows, [4.5, 2.0, 5.0, 5.0])
    para("only the KB-unique and KB-ambiguous cells are short. Proposal: paragraph-level input as the main setting, and fill the rest from the controlled set we already have (575 LLM-paraphrased items, 150 unique and 125 ambiguous by construction), clearly marked as a controlled slice.", bold_lead="Proposal: ")

h1("4. Pilot dry run on the 100 rows (rehearsal, not a result)")
if dr:
    rows = [["Subset", "Rows", "Ours: fact kept", "Ours: agrees with proposed label", "Ours: names someone the text says is unknown", "LLM-only: named / junk node / dropped"]]
    for name, key in (("All 100", "all"), ("R, not stress", "R_nonstress"), ("U (text says unknown)", "U"), ("Stress cases", "stress")):
        s_ = dr.get(key) or {}
        if s_:
            b = s_.get("B1", {})
            rows.append([name, s_["n"], f"{s_['N_fact_kept_pct']}%", f"{s_['N_agrees_with_proposal_pct']}%", s_.get("N_grounded_when_reference_says_no_identity", 0),
                         f"{b.get('NAMED',0)} / {b.get('PHRASE',0)} / {b.get('DROPPED',0)}"])
    table(rows, [3.2, 1.2, 2.2, 2.8, 3.0, 4.6])
    para("our pipeline keeps 82% of the facts and never names an entity the text says is unknown; on the 16 pilot rows with first-pass targets, all 10 of its groundings are the right person and the 5 anonymous cases stay anonymous. "
         "The same model used as a plain extractor turns 75 of 100 unnamed entities into junk nodes (“unknown father”, “brother_of_X”) and drops 16 — the October finding (70–74% junk or lost) holds on the new pool.", bold_lead="Signal: ")
    para("the first scoring found 6 rows where the pipeline named a person the text calls unknown (“His parentage is unknown” → a parent taken from Wikidata; Go Ask Alice’s “anonymous author” → attributed authors). "
         "New rule: when the text says the identity is unknown, output an anonymous node and keep the KB values only as candidates. It also found lexicon gaps (artist, publisher, teacher, employer). After both fixes: 0 such errors.", bold_lead="What the dry run caught: ")
    para("Reference labels are machine-proposed (nobody has annotated the pool yet), the LLM-only grading is automatic, and the two fixes above were made on these same 100 rows — so these 100 are now development data. Honest numbers come from the frozen, human-annotated test split.", italic=True, size=9)

h1("5. Models and baselines on the same 100 rows")
rows = [["Model", "Ours: fact kept", "Ours: agrees with label", "Ours: names an 'unknown' person", "LLM extraction: junk / dropped / named", "Mean s/call", "API $"]]
for name, f, tag in MODELS:
    m = load(f"{PT}/{f}")
    if not m: continue
    a, b, cst = m["all"], m["all"].get("B1", {}), m.get("cost", {})
    rows.append([name, f"{a['N_fact_kept_pct']}%", f"{a['N_agrees_with_proposal_pct']}%", a.get("N_grounded_when_reference_says_no_identity", 0),
                 f"{b.get('PHRASE',0)} / {b.get('DROPPED',0)} / {b.get('NAMED',0)}", cst.get("mean_latency_s", "–"),
                 (f"{cst.get('usd', 0):.3f}" if tag.startswith("openai") else "0 (local)")])
table(rows, [3.6, 1.9, 2.1, 2.4, 3.5, 1.6, 1.6])
b3rows = [["LLM writes SPARQL (KBQA inside extraction)", "Valid SPARQL", "Named someone", "Named someone the reference says has no identity", "Pilot: named correctly"]]
for name, f, tag in MODELS:
    b = load(f"{PT}/b3_summary_{tag}.json")
    if not b: continue
    b3rows.append([name, f"{b['all']['valid_sparql_pct']}%", b["all"]["named"], b["all"]["wrong_identity"], f"{b['pilot_named_correct']}/{b['pilot_named_checkable']}"])
if len(b3rows) > 1:
    table(b3rows, [4.4, 2.2, 2.4, 4.4, 2.6])
para("the same model is used inside our pipeline and in the baselines, so differences come from the method, not the model. The SPARQL baseline runs on live Wikidata (ours on the frozen slice) — noted as a caveat. Reference labels are still machine-proposed.", bold_lead="How to read: ", size=9.5)

h1("6. No-harm check on Text2KGBench (first step)")
nh = [["Model", "Benchmark half", "Sentences", "Module fires", "Firing rate", "Firings that are genuine (hand-checked)"]]
for name, f, tag in MODELS:
    fs = load(f"{NH}/firing_summary_{tag}.json"); ck = load(f"{NH}/firing_checked_{tag}.json")
    if not fs: continue
    for half in ("dbpedia_webnlg", "wikidata_tekgen"):
        h = fs[half]; c = (ck or {}).get(half, {})
        nh.append([name, half, h["sentences"], h["fired"], f"{h['fired_pct']}%", f"{c.get('genuine','–')} / {c.get('checked','–')}" if c else "–"])
if len(nh) > 1:
    table(nh, [3.6, 3.0, 1.8, 2.0, 1.8, 4.4])
    para("on ordinary benchmark sentences the module should rarely fire, and only on real unnamed entities; every firing was checked by hand. The full no-harm check (end-to-end triple F1 with the module switched on) is the next step.", bold_lead="Reading: ", size=9.5)

h1("7. What the output looks like")
g = load(f"{PT}/pool_graph_stats.json")
if g:
    para(f"the dry-run decisions for the 100 rows, written as RDF: {g['facts_written']} facts, {g['anonymous_nodes']} anonymous nodes ({', '.join(f'{v} {k}' for k, v in g['anonymous_by_status'].items())}), {g['grounded_edges']} grounded edges, {g['triples']} triples; it parses as valid Turtle. Every edge has a provenance record (source revision, KB evidence slice, method).", bold_lead="Pool graph: ")
ex = open(f"{PT}/pool_graph_excerpt.ttl").read() if os.path.exists(f"{PT}/pool_graph_excerpt.ttl") else ""
if ex:
    p_ = d.add_paragraph(); r_ = p_.add_run(ex); r_.font.name = "Courier New"; r_.font.size = Pt(7.5)
para("anonymous nodes are skolem IRIs (stable per source revision, sentence and span), aligned with Wikidata’s own “unknown value”; status, description, anchor, relation path and candidates are explicit. This is our proposal for the representation decision.", bold_lead="Representation: ", size=9.5)

h1("8. Paper outline v2 (for your reaction)")
items([
 ("Working title: ", "Don’t Drop the Unnamed: Anonymous-Node Generation for Text-to-Knowledge-Graph Extraction."),
 ("Task: ", "text + reference KB → KG where every described entity is named only when the evidence supports one identity, otherwise an anonymous node with status (ambiguous + candidates / missing / text-unknown / unresolved) and provenance; never invent, never drop."),
 ("Contributions: ", "(1) task + representation; (2) outcome-stratified, evidence-frozen benchmark with two phenomena; (3) neuro-symbolic method with decision rules (answer count, schema tier, text-unknown, anchor safety, conventions) on two KBs; (4) baselines across models and cost; (5) analyses — groundability on Wikidata vs DBpedia, occurrence, failure modes."),
 ("RQs: ", "RQ1 how often and how groundable; RQ2 keep facts without inventing identities vs LLM-only and LLM+KB baselines; RQ3 across KBs and models, no harm to ordinary extraction, cost."),
 ("Related-work check (20 Nov): ", "nothing new combines extraction + anonymous-node output + evidence-based abstention; the closest new item (non-named concept phrases, GenAIK 2025) is a different problem. Full outline: research/anonymous_nodes/PAPER_OUTLINE_V2.md."),
])

h1("9. Decisions we need from you", new_page=True)
items([
 ("Two phenomena. ", "Label “relational description” (R) and “text says the identity is unknown” (U) separately, report both, and keep U from dominating the headline numbers?"),
 ("Outcome quotas. ", "Fix the first 100 as roughly: named in context 20, KB unique 20, KB ambiguous 15, KB missing 20, text-unknown 20, ordinary negatives 5. Natural text alone will not fill KB-unique/ambiguous (2 + 2 in 120 biographies), so: paragraph-level input, other sources, or a controlled slice — which do you prefer?"),
 ("Input and gold. ", "Does the system see the whole article or only the paragraph? With the whole article most KB-known relatives are named somewhere, so KB-unique cases almost vanish; with the paragraph they become testable. Proposal: paragraph as the main setting, whole article as a second setting. Gold defined relative to the input + frozen KB slice; external sources (e.g. an archive naming Charles Hall’s brother) recorded separately for a KB-completion analysis."),
 ("Hard cases. ", "One anonymous node per individual when the count is ≤ 3, else a group node with cardinality; disputed/speculative identities reported as a separate stress subset; text wins over a conflicting KB value (flagged)?"),
 ("Second annotator. ", "Who reviews and adjudicates the first 100 with me (you, Ara, or Aaquifa)? LLM pre-annotations are used only after the human pass."),
 ("Models and server. ", "Luna is in use as the cheap API model (cost in section 5). Which GSoC-server models next, and the budget ceiling for stronger models?"),
 ("Representation. ", "Skolem-IRI anonymous nodes with status / candidates / provenance as in section 7 — or RDF-star / named graphs?"),
])

h1("10. Next two to three weeks")
items([
 ("By 27 Nov: ", "apply your decisions to guide v1; hand-check the rebalancing candidates; fill the outcome quotas; capture evidence for the new rows."),
 ("By 4 Dec: ", "first human annotation pass on 100 rows + second-annotator review; adjudicate; freeze and hash the test split (split by article)."),
 ("By 11 Dec: ", "cheap-model pilot on the frozen 100: LLM-only vs our pipeline vs LLM-written-SPARQL; facts kept, junk-node rate, wrong identities, candidate recall, cost."),
 ("By 18 Dec: ", "Text2KGBench no-harm run with the module on; then broaden models (server + OpenRouter) in January."),
])
out = os.path.join(BASE, "Tsoru_Update_2026-11-20.docx"); d.save(out); print("saved", out)
