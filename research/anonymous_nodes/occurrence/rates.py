"""Per-type sentence rates with Wilson 95% CIs from labels_sample_300.json -> results/stage1_rates.json."""
import json, math, os, collections

def wilson(k, n, z=1.96):
    if n == 0: return (0, 0)
    p = k / n; d = 1 + z*z/n
    c = (p + z*z/(2*n)) / d; h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return (round(max(0, c-h), 4), round(min(1, c+h), 4))

items = json.load(open("labels_sample_300.json"))["items"]
n = len(items)
def rate(pred):
    k = sum(1 for it in items if pred(it["labels"]))
    return {"k": k, "n": n, "rate": round(k/n, 4), "ci95": wilson(k, n)}
has = lambda t: (lambda ls: any(l["type"] == t for l in ls))
out = {t: rate(has(t)) for t in ["T-PRON", "T-DEF", "T-ZERO", "O-PRON", "O-REL", "O-DESC"]}
out["any_unnamed"] = rate(lambda ls: len(ls) > 0)
out["any_topic"] = rate(lambda ls: any(l["type"].startswith("T-") for l in ls))
out["any_other_entity"] = rate(lambda ls: any(l["type"].startswith("O-") for l in ls))
out["O-REL_kb_likely"] = rate(lambda ls: any(l["type"] == "O-REL" and l.get("kb_entity") == "likely" for l in ls))
out["O-REL_or_DESC_kb_likely"] = rate(lambda ls: any(l["type"] in ("O-REL", "O-DESC") and l.get("kb_entity") == "likely" for l in ls))
out["O-REL_spans"] = [(it["pos"], l["span"], l.get("relation"), l.get("kb_entity")) for it in items for l in it["labels"] if l["type"] == "O-REL"]
os.makedirs("results", exist_ok=True)
json.dump(out, open("results/stage1_rates.json", "w"), indent=1, ensure_ascii=False)
for k, v in out.items():
    if k != "O-REL_spans": print(f"{k:24s} {v['k']:3d}/{v['n']}  {v['rate']*100:5.1f}%  CI {v['ci95'][0]*100:.1f}–{v['ci95'][1]*100:.1f}%")
for s in out["O-REL_spans"]: print("  O-REL", s)
