#!/usr/bin/env python3
"""
DROP ATTRIBUTION — why did a proposed candidate not become a triple?

Pilot 3 measured 41 sentences in which Node 1 proposed 110 candidates and not
one survived. From outside the pipeline that is a single undifferentiated
number, which is the same blindness that hid the 18% silent-zero rate until
skipped.jsonl existed. This attributes each death to a stage.

Nothing here modifies the pipeline. `extract_all_triples` already returns its
per-candidate `results` list carrying `status`, `final_triple` and `kept`; every
reason below is derived from that. v14 stays byte-identical to the code behind
the benchmark numbers.
"""

# The emitter sets kept=True only for APPROVED/OVERRIDE. Anything else is a
# verdict from the judge or the tiered SPARQL gate.
PASS_STATUSES = ("APPROVED", "OVERRIDE")


def classify(r, emitted_subjects=None):
    """One result row -> (reason, detail). `r` is an element of out['results'].

    `emitted_subjects` is the set of subjects that DID survive for this sentence.
    It disambiguates the one case the row alone cannot: the compound-literal
    merge sets kept=False on group members it folds into a single comma-joined
    triple (`postalCode "DL1"` + `"DL2"` -> `"DL1, DL2"`). Those look exactly
    like a STRICT rejection from outside — same status, same populated subject —
    and misreading them inflated the strict count by 18% in pilot 4. A subject
    that appears among the survivors was never rejected as unreal."""
    status = r.get("status", "") or ""
    final = r.get("final_triple", "") or ""

    if status == "ERROR":
        return "graph_crash", ""

    if status not in PASS_STATUSES:
        # judge/gate said no; the status IS the reason (REJECTED, OBJ_MISSING, ...)
        return f"verdict_{status.lower()}" if status else "verdict_empty", final[:120]

    if r.get("kept"):
        return None, ""                       # survived to emission

    # Status passed but kept is False. Two distinct causes, distinguishable by
    # whether the subject was ever populated:
    #   sub non-empty -> STRICT_URI_MODE dropped it at the last line of defence
    #   sub empty     -> final_triple did not parse as 3 URIs or a literal form
    if r.get("sub"):
        if emitted_subjects and r["sub"] in emitted_subjects:
            return "literal_merged_or_duplicate", str(r.get("sub"))
        return "strict_subject_not_real", str(r.get("sub"))
    return "malformed_final_triple", final[:120]


def _survivors(results):
    return {r["sub"] for r in results if r.get("kept") and r.get("sub")}


def summarise(results):
    """All results for one sentence -> {reason: count} plus the survivor count."""
    out, kept, surv = {}, 0, _survivors(results)
    for r in results:
        reason, _ = classify(r, surv)
        if reason is None:
            kept += 1
        else:
            out[reason] = out.get(reason, 0) + 1
    return out, kept


def rows_for_log(results, uri, sentence):
    """Per-candidate records for drops.jsonl — one line per dead candidate."""
    recs, surv = [], _survivors(results)
    for r in results:
        reason, detail = classify(r, surv)
        if reason is None:
            continue
        raw = r.get("raw") or {}
        recs.append({
            "abstract_uri": uri,
            "sentence": sentence,
            "reason": reason,
            "detail": detail,
            "proposed_sub": raw.get("subject", ""),
            "proposed_rel": raw.get("predicate", ""),
            "proposed_obj": raw.get("object", ""),
            "status": r.get("status", ""),
        })
    return recs
