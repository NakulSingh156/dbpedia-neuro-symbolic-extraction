"""Hand coding of residual mismatches (after granularity) -> results/disagreement_coding.json.

Random 40 Wikidata (seed 40) and 20 DBpedia (seed 41) residual mismatches, indices in
results/disagreement_sample_idx.json. Codes (Claude, one pass; to be spot-checked by Nakul):
  C convention   same fact, different modelling: demonym vs country ("American" vs United States),
                 historical polity ("Italian" vs Duchy of Milan), sub/superclass ("author" vs writer),
                 player vs sport
  X text error   our Phase-1 extraction or name->QID mapping is wrong ("The Film", "hill", wrong
                 Labour Party, ambiguous subject such as two Avery's Gores)
  G granularity  containment the six Wikidata properties missed (Perth vs City of Joondalup)
  K KB differs   a real difference: another value of a multi-valued relation (farmer vs politician)
                 or KB and text disagree (Uttarakhand vs Lucknow)
"""
import json, math

WD = "X C G X K K C C K C X C C K X C X C C C X K X X X X C G C X C G C C C C C C C C".split()
DBP = "C X X C C C X K X C C C X K X C X K C X".split()

def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z*z/n; c = (p + z*z/(2*n)) / d; h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return [round(max(0, c - h), 3), round(min(1, c + h), 3)]

dec = json.load(open("results/correctness_decomposition.json"))
out = {}
for kb, codes in (("wd", WD), ("dbp", DBP)):
    n = len(codes); share = {c: codes.count(c) / n for c in "CXGK"}
    d = dec[kb]; resid = d["genuine_disagreement"]
    agree = d["exact_match"] + d["granularity"] + resid * (share["C"] + share["G"])
    valid = d["judged"] - resid * share["X"]
    out[kb] = {"sample": n, "counts": {c: codes.count(c) for c in "CXGK"},
               "K_share_ci95": wilson(codes.count("K"), n),
               "est_agreement_excl_text_errors_pct": round(100 * agree / valid, 1),
               "est_true_disagreement_pct": round(100 * resid * share["K"] / valid, 1),
               "est_text_error_pct_of_judged": round(100 * resid * share["X"] / d["judged"], 1)}
json.dump({"codes": {"wd": WD, "dbp": DBP}, "summary": out}, open("results/disagreement_coding.json", "w"), indent=1)
for kb, v in out.items(): print(kb, v)
