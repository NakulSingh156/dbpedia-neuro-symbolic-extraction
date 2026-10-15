"""Blind 50 for the second annotator (Nakul): random 50 of sample_300, no labels shown -> blind_50_for_nakul.csv.
Fill `any_unnamed` (y/n) and `labels` (e.g. "T-PRON:He; O-REL:his brother") following GUIDELINES.md.
Then run kappa.py."""
import csv, json, random
S = [json.loads(l) for l in open("sample_300.jsonl")]
pick = sorted(random.Random(50).sample(range(len(S)), 50))
with open("blind_50_for_nakul.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["pos", "id", "topic", "previous_sentence", "sentence", "any_unnamed", "labels"])
    for i in pick:
        s = S[i]
        w.writerow([i + 1, s["id"], s["topic"].split("/")[-1].replace("_", " "), s["prev"] or "", s["sentence"], "", ""])
print("wrote 50:", [i + 1 for i in pick])
