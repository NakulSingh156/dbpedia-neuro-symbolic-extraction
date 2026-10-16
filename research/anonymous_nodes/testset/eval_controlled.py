"""First end-to-end run of approach N on the controlled PROTOTYPE items (testset/prototype/realised.jsonl).
M1 (detector + keep) reads the realised text; M2 is trivial here (every anchor is the text's topic, whose QID a
real pipeline knows from the article); M3-M6 as in pipeline_dev.py, with simulated-missing items answered on a
KB where the hidden fact is masked. Scored against the gold type/answers. PROTOTYPE: templated sentences,
no human check yet. -> testset/prototype/eval_controlled_<model>.json"""
import json, os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from generic.detect import detect, keep          # noqa: E402
from generic.ir import Description               # noqa: E402
from generic.kb_wikidata import WikidataKB       # noqa: E402

model = next((a for a in sys.argv[1:] if not a.startswith("--")), "llama3.1:8b")
kb = WikidataKB()
items = [json.loads(l) for l in open(os.path.join(HERE, "prototype/realised.jsonl"))]
CACHE = os.path.join(HERE, f"prototype/detect_cache_{model.replace(':', '_')}.json")
cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
GOLD2OUT = {"unique": "GROUNDED", "ambiguous": "AMBIGUOUS", "none": "MISSING"}
rows = []
for n, it in enumerate(items):
    name = it["intro"].split(" is ")[0]
    if it["id"] not in cache:
        found, err = detect(it["sentence"], name, it["text"], model=model)
        cache[it["id"]] = {"found": [json.loads(d.to_json()) for d in found], "err": err}
        if n % 20 == 0:
            json.dump(cache, open(CACHE, "w"), ensure_ascii=False); print(f"  {n}/{len(items)}", flush=True)
    found = [d for d in (Description.from_dict(x) for x in cache[it["id"]]["found"]) if keep(d, it["sentence"])]
    pick = next((d for d in found if it["noun"] in d.mention.lower()), found[0] if found else None)
    if not pick:
        out, ans = "NOT-DETECTED", []
    elif "wikidata" not in pick.paths:
        out, ans = "UNRESOLVED", []
    else:
        r = kb.values(it["anchor_qid"], pick.paths["wikidata"], pick.constraints.gender,
                      mask=it.get("hidden_truth", []) if it["simulated"] else ())
        ans = r["known"]; out = "GROUNDED" if len(ans) == 1 else "AMBIGUOUS" if len(ans) > 1 else "MISSING"
    want = GOLD2OUT[it["gold_type"]]
    correct = out == want and (out != "GROUNDED" or ans == it["gold"]) and (out != "AMBIGUOUS" or sorted(ans) == sorted(it["gold"]))
    rows.append({"id": it["id"], "noun": it["noun"], "form": it["form"], "pop_tier": it["pop_tier"], "gold_type": it["gold_type"],
                 "simulated": it["simulated"], "tier": it["tier"], "want": want, "got": out, "answers": ans, "gold": it["gold"],
                 "correct": correct, "wrong_identity": out == "GROUNDED" and ans != it["gold"],
                 "relations": pick.relation_phrases if pick else None})
json.dump(cache, open(CACHE, "w"), ensure_ascii=False)

def acc(sel):
    s = [r for r in rows if sel(r)]
    return {"n": len(s), "correct": sum(r["correct"] for r in s), "pct": round(100 * sum(r["correct"] for r in s) / len(s), 1) if s else None,
            "wrong_identity": sum(r["wrong_identity"] for r in s)}
summ = {"model": model, "overall": acc(lambda r: True),
        "by_gold": {g + ("_sim" if sim else ""): acc(lambda r, g=g, sim=sim: r["gold_type"] == g and r["simulated"] == sim)
                    for g, sim in (("unique", False), ("ambiguous", False), ("none", False), ("none", True))},
        "by_pop": {t: acc(lambda r, t=t: r["pop_tier"] == t) for t in ("tail", "mid", "head")},
        "by_form": {f: acc(lambda r, f=f: r["form"] == f) for f in ("possessive", "of_phrase", "pronoun")},
        "by_noun": {nn: acc(lambda r, nn=nn: r["noun"] == nn) for nn in sorted({r["noun"] for r in rows})},
        "outcomes": dict(collections.Counter((r["want"], r["got"]) for r in rows).most_common())}
summ["outcomes"] = {f"{a}->{b}": v for (a, b), v in summ["outcomes"].items()}
json.dump({"summary": summ, "rows": rows}, open(os.path.join(HERE, f"prototype/eval_controlled_{model.replace(':', '_')}.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps(summ, indent=1))
