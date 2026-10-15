"""Hand verification of stage-2 scan hits (results/scan_hits.jsonl) -> results/scan_verified.json + results/occurrence_summary.json.

GENUINE lists every hit sentence that holds a real O-REL (non-topic entity picked out by a relation,
not named in that sentence). All other hit sentences were checked and rejected: named in the sentence
(apposition or copula, "His father was Seisyll ap Clydog"), a predicate on the topic ("the son of X",
"the founder of X"), debuts/events, or generic groups. The `apposition` pre-tag is unreliable for
of-phrases ("the father-in-law of Isaac N. Deadrick"), so every hit was read.
"""
import json, math

def R(span, rel, named, plural, kb, note=None):
    d = {"span": span, "relation": rel, "named_elsewhere": named, "plural": plural, "kb_entity": kb}
    if note: d["note"] = note
    return d

GENUINE = {
  "00506": [R("His brother", "sibling", "no", "no", "likely")],
  "00951": [R("the father-in-law of Isaac N. Deadrick", "father-in-law", "no", "no", "unlikely")],
  "00964": [R("His namesake nephew", "nephew", "no", "no", "likely")],
  "01055": [R("the movement for its creation", "movement for", "no", "no", "likely", "borderline; Pakistan Movement")],
  "01649": [R("its ruler", "ruler", "no", "no", "likely", "borderline; an office holder")],
  "01816": [R("his wife", "spouse", "no", "no", "unlikely")],
  "01981": [R("the founder of Mérida", "founder", "no", "no", "likely"),
            R("the grandson of the founder of Mérida", "grandson", "no", "no", "unlikely", "nested")],
  "02054": [R("a financial secretary", "father", "no", "no", "unlikely", "'the son of a financial secretary'")],
  "02126": [R("his daughter", "child", "no", "no", "unlikely")],
  "02127": [R("another of his daughters", "child", "no", "no", "unlikely")],
  "02528": [R("his dead son", "child", "no", "no", "unlikely")],
  "03186": [R("her father", "father", "yes", "no", "likely"),
            R("her father's quiz show", "show of", "no", "no", "likely", "You Bet Your Life; nested")],
  "03360": [R("her son", "child", "yes", "no", "likely"), R("her grandson", "grandchild", "yes", "no", "likely")],
  "03715": [R("his father", "father", "no", "no", "unlikely")],
  "03772": [R("the wife of Guilhem de Montanhagol", "spouse", "no", "no", "unlikely")],
  "03773": [R("his brother-in-law", "brother-in-law", "no", "no", "unlikely")],
  "03828": [R("its political leaders", "leader", "no", "yes", "unlikely")],
  "04298": [R("his brother", "sibling", "no", "no", "unlikely")],
  "04484": [R("its genus", "genus", "no", "no", "likely")],
  "04769": [R("a daimyo of the Akizuki clan", "father", "no", "no", "likely", "'the second son of a daimyo ...'")],
  "04770": [R("His mother", "mother", "no", "no", "unlikely"),
            R("the fourth head of Yonezawa", "head of", "no", "no", "likely", "nested")],
  "05017": [R("his father", "father", "yes", "no", "likely")],
  "05021": [R("his colleagues", "colleague", "no", "yes", "unlikely")],
  "05035": [R("His father", "father", "yes", "no", "likely")],
}

def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z*z/n; c = (p + z*z/(2*n)) / d; h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return [round(max(0, c-h), 5), round(min(1, c+h), 5)]

hits = [json.loads(l) for l in open("results/scan_hits.jsonl")]
N = sum(1 for _ in open("all_sentences.jsonl"))
assert set(GENUINE) <= {h["id"] for h in hits}
rows = [{"id": h["id"], "topic": h["topic"], "sentence": h["sentence"], "genuine": h["id"] in GENUINE,
         "o_rel": GENUINE.get(h["id"], [])} for h in hits]
json.dump(rows, open("results/scan_verified.json", "w"), indent=1, ensure_ascii=False)

def count(pred):
    k = sum(1 for v in GENUINE.values() if any(pred(x) for x in v))
    return {"k": k, "n": N, "rate": round(k/N, 5), "ci95": wilson(k, N)}
stage1 = json.load(open("results/stage1_rates.json"))
summary = {
  "sentences": N, "scan_hit_sentences": len(hits),
  "scan_precision": round(len(GENUINE)/len(hits), 3),
  "scan_O-REL_any": count(lambda x: True),
  "scan_O-REL_not_named_elsewhere": count(lambda x: x["named_elsewhere"] == "no"),
  "scan_O-REL_kb_likely_not_named": count(lambda x: x["named_elsewhere"] == "no" and x["kb_entity"] == "likely"),
  "scan_recall_on_stage1": {"O-REL_sentences": "2/8", "O-REL_kb_likely_sentences": "2/3",
                            "missed": "plural groups, implicit topic anchors ('The third season', 'The present building'), "
                                      "bridging ('The English adaptation'), 'his cabinet', 'eight children'"},
  "stage1": {k: stage1[k] for k in ["any_unnamed", "any_topic", "any_other_entity", "O-REL", "O-REL_kb_likely", "O-DESC"]},
}
json.dump(summary, open("results/occurrence_summary.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in summary.items() if k != "stage1"}, indent=1))
