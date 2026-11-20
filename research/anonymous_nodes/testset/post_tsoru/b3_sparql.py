"""Baseline B3 — LLM writes SPARQL (KBQA inside extraction), on the 100-row pool. Same oracle anchor QID as ours.
Step 1: LLM writes a SPARQL SELECT ?x for the described entity, given sentence + context + anchor QID.
Step 2: run it on Wikidata (QLever, cached; live, NOT the frozen slice — noted in the summary).
Step 3: 0 rows -> UNKNOWN; 1 row -> named; >1 rows -> the LLM picks one or answers UNKNOWN (given labels).
Scored against the triage reference: NAMED where the reference has no identity (TEXT_UNKNOWN / KB_MISSING) = wrong identity.
-> b3_<model>.csv, b3_summary_<model>.json"""
import csv, json, os, re, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from generic.llm import llm_json, CALLS   # noqa: E402
from generic.kb_wikidata import WikidataKB, KBUnavailable   # noqa: E402
MODEL = sys.argv[1] if len(sys.argv) > 1 else "llama3.1:8b"
TAG = MODEL.replace("openrouter:", "").replace("/", "_").replace(":", "_")
kb = WikidataKB()
tri = {r["item_id"]: r for r in csv.DictReader(open(os.path.join(HERE, "pool_triage_v1_2026-11-19.csv")))}
pool = {r["item_id"]: r for r in csv.DictReader(open(os.path.join(HERE, "pool_v1_2026-11-19.csv")))}
first = {r["item_id"]: r for r in csv.DictReader(open(os.path.join(HERE, "pilot_first_pass_annotations_v0.csv")))}
P1 = """You extract knowledge-graph facts. The text describes an entity without naming it.
Text: {context}
Sentence: "{sentence}"
Described entity: "{span}" (described relative to {anchor}, Wikidata item {qid}).
Write ONE SPARQL query for the Wikidata Query Service that returns the described entity as ?x, using wd: and wdt: prefixes
(e.g. SELECT ?x WHERE {{ wd:{qid} wdt:P22 ?x }}). Reply as JSON: {{"sparql": "..."}}"""
P2 = """Text: {context}
Sentence: "{sentence}"
Which of these Wikidata entities is "{span}"? Candidates: {cands}
If the text does not let you decide, or says the identity is unknown, answer UNKNOWN. Reply as JSON: {{"answer": "<QID or UNKNOWN>"}}"""
PFX = "PREFIX wd: <http://www.wikidata.org/entity/> PREFIX wdt: <http://www.wikidata.org/prop/direct/> PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> "
CACHE = os.path.join(HERE, f"b3_cache_{TAG}.json"); cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
rows = []
for n, iid in enumerate(tri, 1):
    t, p = tri[iid], pool[iid]
    if not t["anchor_qid"]: continue
    if iid not in cache:
        n0 = len(CALLS)
        ctx = (p.get("context") or "")[:1500]
        j, _ = llm_json(P1.format(context=ctx, sentence=p["sentence"], span=p["target_span"], anchor=p["source_name"], qid=t["anchor_qid"]), MODEL, max_tokens=300)
        q = (j or {}).get("sparql", "") if isinstance(j, dict) else ""
        res, err = [], None
        if q:
            try:
                q2 = q if "PREFIX" in q.upper() else PFX + q
                res = sorted({b["x"]["value"].rsplit("/", 1)[1] for b in kb.sparql(q2) if "x" in b and "/entity/Q" in b["x"]["value"]})[:25]
            except (KBUnavailable, Exception) as e:
                err = str(e)[:120]
        if len(res) == 1:
            ans = res[0]
        elif len(res) > 1:
            labs = kb.labels(res)
            j2, _ = llm_json(P2.format(context=ctx, sentence=p["sentence"], span=p["target_span"], cands="; ".join(f"{q_} = {labs.get(q_, q_)}" for q_ in res)), MODEL, max_tokens=60)
            ans = (j2 or {}).get("answer", "UNKNOWN") if isinstance(j2, dict) else "UNKNOWN"
        else:
            ans = "UNKNOWN"
        cache[iid] = {"sparql": q, "results": res, "error": err, "answer": ans, "calls": CALLS[n0:]}
        json.dump(cache, open(CACHE, "w"), ensure_ascii=False)
        if n % 10 == 0: print(f"  {n}/{len(tri)}", flush=True)
    c = cache[iid]; exp = t["proposed_outcome"]
    named = bool(re.fullmatch(r"Q\d+", str(c["answer"])))
    gold = set(first.get(iid, {}).get("first_pass_target_qids", "").replace(";", " ").replace("|", " ").split())
    rows.append({"item_id": iid, "phenomenon": t["phenomenon"], "flags": t["flags"], "reference": exp, "sparql_ok": bool(c["sparql"]) and not c["error"],
                 "n_results": len(c["results"]), "answer": c["answer"],
                 "wrong_identity": named and exp in ("TEXT_UNKNOWN", "KB_MISSING", "ANCHOR_NOT_IN_KB"),
                 "named_correct_on_pilot": (named and c["answer"] in gold) if gold and not any(g.startswith("anon") for g in gold) else None})
w = csv.DictWriter(open(os.path.join(HERE, f"b3_{TAG}.csv"), "w", newline=""), fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
calls = [x for v in cache.values() for x in v.get("calls", [])]
def summ(sel):
    s = [r for r in rows if sel(r)]
    return {"n": len(s), "named": sum(re.fullmatch(r"Q\d+", str(r["answer"])) is not None for r in s), "wrong_identity": sum(r["wrong_identity"] for r in s),
            "valid_sparql_pct": round(100 * sum(r["sparql_ok"] for r in s) / len(s), 1) if s else None}
out = {"model": MODEL, "kb": "live Wikidata via QLever (not the frozen slice)", "all": summ(lambda r: True),
       "U": summ(lambda r: r["phenomenon"] == "U"), "R_nonstress": summ(lambda r: r["phenomenon"] == "R" and "stress" not in r["flags"]),
       "pilot_named_correct": sum(1 for r in rows if r["named_correct_on_pilot"]), "pilot_named_checkable": sum(1 for r in rows if r["named_correct_on_pilot"] is not None),
       "cost": {"calls": len(calls), "prompt_tokens": sum(x.get("prompt_tokens") or 0 for x in calls), "completion_tokens": sum(x.get("completion_tokens") or 0 for x in calls),
                "mean_latency_s": round(sum(x["latency_s"] for x in calls) / len(calls), 2) if calls else None}}
json.dump(out, open(os.path.join(HERE, f"b3_summary_{TAG}.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
