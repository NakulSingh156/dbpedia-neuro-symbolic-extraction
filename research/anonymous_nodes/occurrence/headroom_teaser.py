"""Headroom teaser (NOT the real baseline): real relational descriptions from the scan
(scan_verified.py), grounded on Wikidata with a hand-written description (= an oracle parse of
M1-M3), and the same descriptions put to local LLMs closed-book (name it, or UNKNOWN).
-> results/headroom_teaser.json ; grading by hand in headroom_graded.py
"""
import json, os, sys, time, requests
from urllib.parse import unquote
HERE = os.path.dirname(os.path.abspath(__file__))
QLEVER = "https://qlever.dev/api/wikidata"
UA = {"User-Agent": "nef-research/0.1 (https://github.com/NakulSingh156/dbpedia-neuro-symbolic-extraction; research script)"}
WD, WDT = "http://www.wikidata.org/entity/", "http://www.wikidata.org/prop/direct/"
MALE, FEMALE = "Q6581097", "Q6581072"

# (sentence id, description span, anchor Wikipedia title, alternative paths, gender)
ITEMS = [
 ("00506", "His brother", "Arthur Winter", [["P3373"]], MALE),
 ("00951", "the father-in-law of Isaac N. Deadrick", "Isaac N. Deadrick", [["P26", "P22"]], MALE),
 ("00964", "His namesake nephew", "Carlo Zucchi (general)", [["P3373", "P40"]], MALE),
 ("01649", "its ruler", "Negeri Sembilan", [["P35"]], None),
 ("01816", "his wife", "George Hyde (Knight of the Bath)", [["P26"]], FEMALE),
 ("01981", "the founder of Mérida", "Mérida, Yucatán", [["P112"]], None),
 ("01981", "the grandson of the founder of Mérida", "Mérida, Yucatán", [["P112", "P40", "P40"]], MALE),
 ("02054", "a financial secretary (his father)", "Hermann Pister", [["P22"]], MALE),
 ("02126", "his daughter", "Hrafna-Flóki Vilgerðarson", [["P40"]], FEMALE),
 ("02127", "another of his daughters", "Hrafna-Flóki Vilgerðarson", [["P40"]], FEMALE),
 ("02528", "his dead son", "Kanakaraya Mudali", [["P40"]], MALE),
 ("03186", "her father", "Miriam Marx", [["P22"]], MALE),
 ("03360", "her son", "Nefertkau I", [["P40"]], MALE),
 ("03360", "her grandson", "Nefertkau I", [["P40", "P40"]], MALE),
 ("03715", "his father", "Philipp van Limborch", [["P22"]], MALE),
 ("03772", "the wife of Guilhem de Montanhagol", "Guilhem de Montanhagol", [["P26"]], FEMALE),
 ("03773", "his brother-in-law", "Pons Santolh", [["P26", "P3373"], ["P3373", "P26"]], MALE),
 ("04298", "his brother", "Sol Levi", [["P3373"]], MALE),
 ("04484", "its genus", "Tautog", [["P171"]], None),
 ("04769", "a daimyo of the Akizuki clan (his father)", "Uesugi Harunori", [["P22"]], MALE),
 ("04770", "His mother", "Uesugi Harunori", [["P25"]], FEMALE),
 ("05017", "his father", "William Busfield", [["P22"]], MALE),
 ("05035", "His father", "William Lloyd George, 3rd Viscount Tenby", [["P22"]], MALE),
]

def qid(title):
    j = requests.get("https://en.wikipedia.org/w/api.php", headers=UA, timeout=60, params={
        "action": "query", "prop": "pageprops", "ppprop": "wikibase_item", "redirects": 1,
        "titles": title, "format": "json"}).json()
    p = next(iter(j["query"]["pages"].values()))
    return p.get("pageprops", {}).get("wikibase_item")

def wq(q):
    for i in range(6):
        r = requests.post(QLEVER, data={"query": q}, headers={**UA, "Accept": "application/sparql-results+json"}, timeout=120)
        if r.status_code == 200: return r.json()["results"]["bindings"]
        time.sleep(5 * (i + 1))
    raise RuntimeError(r.text[:200])

def ground(q, paths, gender):
    other = {MALE: FEMALE, FEMALE: MALE}.get(gender)
    unions = " UNION ".join("{ <%s%s> %s ?x }" % (WD, q, "/".join(f"<{WDT}{p}>" for p in path)) for path in paths)
    flt = f"FILTER NOT EXISTS {{ ?x <{WDT}P21> <{WD}{other}> }}" if other else ""
    rows = wq(f"""SELECT DISTINCT ?x ?l WHERE {{ {unions} {flt}
                 OPTIONAL {{ ?x <http://www.w3.org/2000/01/rdf-schema#label> ?l FILTER(LANG(?l) = "en") }} }}""")
    ans = [(x["x"]["value"].rsplit("/", 1)[1], x.get("l", {}).get("value")) for x in rows]
    known = [a for a in ans if not "/.well-known/genid/" in a[0] and a[0].startswith("Q")]
    unknown = len(ans) - len(known)
    out = "GROUNDED" if len(known) == 1 else "AMBIGUOUS" if len(known) > 1 else ("UNKNOWN-VALUE" if unknown else "MISSING")
    return out, known, unknown

A = [json.loads(l) for l in open(os.path.join(HERE, "all_sentences.jsonl"))]
by_id = {x["id"]: x for x in A}
abstract = {}
for x in A: abstract.setdefault(x["abstract_uri"], []).append(x["sentence"])

def ask(model, item):
    sid, span = item[0], item[1].split(" (")[0]
    x = by_id[sid]
    prompt = (f"Text (Wikipedia abstract about {x['topic']}):\n{' '.join(abstract[x['abstract_uri']])}\n\n"
              f"In the sentence \"{x['sentence']}\", the phrase \"{span}\" refers to an entity that the text does not name.\n"
              "Who or what exactly is it? Give its full name. If you do not know for sure, answer UNKNOWN.\n"
              'Reply as JSON: {"answer": "<full name or UNKNOWN>", "confidence": "high|medium|low"}')
    r = requests.post("http://localhost:11434/api/generate", timeout=300, json={
        "model": model, "prompt": prompt, "format": "json", "stream": False, "options": {"temperature": 0}})
    try:
        return json.loads(r.json()["response"])
    except Exception:
        return {"answer": r.json().get("response", "")[:200], "confidence": "parse-error"}

out = []
for it in ITEMS:
    q = qid(it[2]); time.sleep(1)
    kb = ground(q, it[3], it[4]) if q else ("ANCHOR-NOT-IN-KB", [], 0)
    row = {"id": it[0], "span": it[1], "anchor": it[2], "anchor_qid": q, "paths": it[3], "gender": it[4],
           "kb_outcome": kb[0], "kb_answers": kb[1], "kb_unknown_values": kb[2],
           "llm": {m: ask(m, it) for m in ("qwen2.5:7b", "llama3.1:8b")}}
    out.append(row)
    print(f'{it[0]} {it[1][:38]:38s} | KB {kb[0]:14s} {[a[1] for a in kb[1]][:3]} | '
          f'qwen: {row["llm"]["qwen2.5:7b"].get("answer")!s:28.28s} | llama: {row["llm"]["llama3.1:8b"].get("answer")!s:28.28s}', flush=True)
json.dump(out, open(os.path.join(HERE, "results/headroom_teaser.json"), "w"), indent=1, ensure_ascii=False)
