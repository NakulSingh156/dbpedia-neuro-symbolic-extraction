"""Pilot DRY RUN on the 100-row pool (19 Nov). Rehearses the evaluation on the new format; NOT a result:
the reference labels are machine-proposed (pool_triage_v1) and no human has annotated the pool yet.

N  (ours): M1 detector (Llama-3.1-8B, keep v3) on the sentence + the row's context; the target detection is the
           one whose relation matches the row; KB answers come from the FROZEN evidence slice (same evidence as gold);
           decision: GROUNDED / AMBIGUOUS / MISSING / UNKNOWN_VALUE; safety: pronoun_anchor_ambiguous -> UNRESOLVED.
B1 (LLM only, extraction mode): "extract triples with canonical entity names"; auto-graded per row:
           NAMED (a capitalised name fills the target slot), PHRASE (the description itself becomes a node),
           DROPPED (no triple carries the relation).
-> pilot_dryrun_2026-11-19.csv, pilot_dryrun_summary.json
"""
import csv, json, os, re, sys, collections, requests
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
from generic.detect import detect, keep, pronoun_anchor_ambiguous, text_says_unknown   # noqa: E402
from generic.lexicon import expand   # noqa: E402
from generic.ir import Description                                  # noqa: E402

MODEL = next((a for a in sys.argv[1:] if not a.startswith("--")), "llama3.1:8b")
TAG = MODEL.replace("openrouter:", "").replace("/", "_").replace(":", "_")
from generic import llm as LLM   # noqa: E402
tri = {r["item_id"]: r for r in csv.DictReader(open(os.path.join(HERE, "pool_triage_v1_2026-11-19.csv")))}
pool = {r["item_id"]: r for r in csv.DictReader(open(os.path.join(HERE, "pool_v1_2026-11-19.csv")))}
ev = json.load(open(os.path.join(HERE, "wikidata_slice_2026-11-19/wikidata_evidence_slice.json")))
ents, sex = ev["entities"], ev.get("target_sex_P21", {})
MALE, FEMALE = "Q6581097", "Q6581072"
CACHE = os.path.join(HERE, "pilot_dryrun_cache.json" if MODEL == "llama3.1:8b" else f"pilot_dryrun_cache_{TAG}.json")
cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}

def slice_values(qid, props, gender):
    vals, some = [], 0
    for p in props:
        for st in ents.get(qid, {}).get("claims", {}).get(p, []):
            sn = st.get("mainsnak", {})
            if sn.get("snaktype") == "somevalue": some += 1; continue
            v = sn.get("datavalue", {}).get("value", {})
            if isinstance(v, dict) and v.get("id"): vals.append(v["id"])
    other = {"male": FEMALE, "female": MALE}.get(gender)
    return [v for v in vals if not (other and other in sex.get(v, []))], some

B1_PROMPT = """You are building a knowledge graph from Wikipedia text.
Context: {context}
Extract every factual triple stated in this sentence: "{sentence}"
Use canonical entity names (as Wikipedia article titles) for subjects and objects; resolve pronouns and descriptions.
Reply as JSON: {{"triples": [["subject", "relation", "object"], ...]}}"""

def b1(sentence, context):
    j, meta = LLM.llm_json(B1_PROMPT.format(context=context, sentence=sentence), MODEL, max_tokens=600)
    return (j or {}).get("triples", []) if isinstance(j, dict) else []

def grade_b1(triples, rel_words, anchor):
    hit = [t for t in triples if isinstance(t, list) and len(t) == 3 and any(w in " ".join(map(str, t)).lower() for w in rel_words)]
    if not hit: return "DROPPED"
    for t in hit:
        for slot in (t[0], t[2]):
            s = str(slot)
            if any(w in s.lower() for w in rel_words) or "_of_" in s or s.lower().startswith(("his ", "her ", "the ", "a ", "an ", "unknown")):
                return "PHRASE"
    return "NAMED"

rows = []
items = [i for i, t in tri.items() if t["proposed_outcome"] not in ("UNMAPPED_RELATION",)]
for n, iid in enumerate(items, 1):
    t, p = tri[iid], pool[iid]
    ctx = (p.get("context") or "")[:1500]
    if iid not in cache:
        n0 = len(LLM.CALLS)
        found, err = detect(p["sentence"], p["source_name"], ctx + " " + p["sentence"], model=MODEL)
        b1_out = b1(p["sentence"], ctx)
        cache[iid] = {"found": [json.loads(d.to_json()) for d in found], "err": err, "b1": b1_out, "calls": LLM.CALLS[n0:]}
        json.dump(cache, open(CACHE, "w"), ensure_ascii=False)
        if n % 10 == 0: print(f"  {n}/{len(items)}", flush=True)
    rel_words = [w for w in re.findall(r"[a-z\-]+", (t["target_span"] + " " + p["relation_or_path"]).lower())
                 if w in {"brother", "sister", "sibling", "siblings", "twin", "father", "mother", "parent", "parents", "wife", "husband",
                          "spouse", "son", "daughter", "child", "children", "teacher", "author", "artist", "painter", "publisher",
                          "employer", "company", "brothers", "sisters", "sons", "daughters", "benefactor", "creator"}] or ["of"]
    found = []
    for x in cache[iid]["found"]:
        d = Description.from_dict(x)      # re-expand with the current lexicon (v1 adds artist/publisher/teacher/employer)
        d.paths = {kb: expand(d.relation_phrases, kb)[0] for kb in ("wikidata", "dbpedia") if expand(d.relation_phrases, kb)[0]}
        if keep(d, p["sentence"]): found.append(d)
    pick = next((d for d in found if any(w.rstrip("s") in " ".join(d.relation_phrases) for w in rel_words)), None)
    if not pick:
        out, ans = "NOT-DETECTED", []
    elif pronoun_anchor_ambiguous(pick, p["sentence"]):
        out, ans = "UNRESOLVED", []
    else:
        props = t["relation_props"].split("|") if t["relation_props"] else []
        ans, some = slice_values(t["anchor_qid"], props, t["gender"]) if props and t["anchor_qid"] else ([], 0)
        out = "GROUNDED" if len(ans) == 1 else "AMBIGUOUS" if ans else ("UNKNOWN_VALUE" if some else "MISSING")
        if text_says_unknown(pick, p["sentence"]):
            out = "TEXT_UNKNOWN"          # anonymous node; KB values kept only as candidates
    exp = t["proposed_outcome"]
    expect = {"KB_UNIQUE": "GROUNDED", "KB_AMBIGUOUS": "AMBIGUOUS", "KB_MISSING": "MISSING", "KB_UNKNOWN_VALUE": "UNKNOWN_VALUE",
              "TEXT_UNKNOWN": "ANON", "ANCHOR_NOT_IN_KB": "ANON", "NAMED_IN_CONTEXT": "NAMED"}.get(exp)
    kept = out in ("GROUNDED", "AMBIGUOUS", "MISSING", "UNKNOWN_VALUE", "TEXT_UNKNOWN")
    agree = ((expect == out) or (expect == "ANON" and out in ("MISSING", "UNKNOWN_VALUE", "AMBIGUOUS", "TEXT_UNKNOWN"))
             or (expect == "NAMED" and out == "GROUNDED"))         # a named-in-context entity is correctly grounded
    wrong_identity = out == "GROUNDED" and exp in ("TEXT_UNKNOWN", "KB_MISSING", "ANCHOR_NOT_IN_KB")
    rows.append({"item_id": iid, "phenomenon": t["phenomenon"], "flags": t["flags"], "proposed_outcome": exp, "N_outcome": out,
                 "N_answers": " ".join(ans), "N_fact_kept": kept, "N_agrees_with_proposal": agree, "N_grounded_when_reference_says_no_identity": wrong_identity,
                 "B1_grade": grade_b1(cache[iid]["b1"], rel_words, p["source_name"]), "sentence": p["sentence"][:200]})
json.dump(cache, open(CACHE, "w"), ensure_ascii=False)
w = csv.DictWriter(open(os.path.join(HERE, "pilot_dryrun_2026-11-19.csv" if MODEL == "llama3.1:8b" else f"pilot_dryrun_{TAG}.csv"), "w", newline=""), fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

def summ(sel):
    s = [r for r in rows if sel(r)]
    if not s: return {}
    return {"n": len(s), "N_fact_kept_pct": round(100 * sum(r["N_fact_kept"] for r in s) / len(s), 1),
            "N_agrees_with_proposal_pct": round(100 * sum(r["N_agrees_with_proposal"] for r in s) / len(s), 1),
            "N_grounded_when_reference_says_no_identity": sum(r["N_grounded_when_reference_says_no_identity"] for r in s),
            "N_outcomes": dict(collections.Counter(r["N_outcome"] for r in s)),
            "B1": dict(collections.Counter(r["B1_grade"] for r in s))}
out = {"all": summ(lambda r: True), "R_nonstress": summ(lambda r: r["phenomenon"] == "R" and "stress" not in r["flags"]),
       "U": summ(lambda r: r["phenomenon"] == "U"), "stress": summ(lambda r: "stress" in r["flags"]),
       "by_proposed_outcome": {k: summ(lambda r, k=k: r["proposed_outcome"] == k) for k in sorted({r["proposed_outcome"] for r in rows})}}
calls = [c for v in cache.values() for c in v.get("calls", [])]
out["cost"] = {"model": MODEL, "calls": len(calls), "errors": sum(1 for c in calls if c.get("error")),
               "prompt_tokens": sum(c.get("prompt_tokens") or 0 for c in calls), "completion_tokens": sum(c.get("completion_tokens") or 0 for c in calls),
               "usd": round(sum(c.get("cost_usd") or 0 for c in calls), 4), "mean_latency_s": round(sum(c["latency_s"] for c in calls) / len(calls), 2) if calls else None}
json.dump(out, open(os.path.join(HERE, "pilot_dryrun_summary.json" if MODEL == "llama3.1:8b" else f"pilot_dryrun_summary_{TAG}.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
