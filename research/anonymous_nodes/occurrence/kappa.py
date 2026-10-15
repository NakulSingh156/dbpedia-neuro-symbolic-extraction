"""Cohen's kappa between Claude's first pass and Nakul's blind 50 on (a) any unnamed reference, (b) any O-REL."""
import csv, json
C = {it["id"]: it["labels"] for it in json.load(open("labels_sample_300.json"))["items"]}
rows = [r for r in csv.DictReader(open("blind_50_for_nakul.csv")) if r["any_unnamed"].strip()]
def kappa(a, b):
    n = len(a); po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n; pe = pa*pb + (1-pa)*(1-pb)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0
c_any = [bool(C[r["id"]]) for r in rows]; n_any = [r["any_unnamed"].strip().lower().startswith("y") for r in rows]
c_rel = [any(l["type"] == "O-REL" for l in C[r["id"]]) for r in rows]; n_rel = ["O-REL" in r["labels"] for r in rows]
print(f"n={len(rows)} | kappa any_unnamed={kappa(c_any, n_any)} | kappa O-REL={kappa(c_rel, n_rel)} (O-REL is rare; also report raw agreement)")
print("disagreements:", [r["pos"] for r, a, b in zip(rows, c_any, n_any) if a != b])
