"""M7 OutputWriter — anonymous-node KG output (METHODOLOGY §3.5; proposal for Tsoru's representation decision).

Representation (portable Turtle, no RDF-star needed):
  grounded:   <anchor> wdt:Pxx wd:Qtarget .
  anonymous:  <anchor> wdt:Pxx <skolem IRI> .   <skolem IRI> a nef:AnonymousEntity ; nef:status nef:Missing|Ambiguous|
              TextUnknown|Unresolved|KBUnknownValue ; nef:describedAs "his younger brother"@en ; rdfs:label "<span> of <anchor>"@en ;
              nef:anchor wd:Q ; nef:path "P3373" ; nef:gender ; nef:candidate wd:Q… .
  every fact: a nef:Assertion node (subject, predicate, object, status, grounding tier, source revision, KB evidence slice
              hash, method) — the provenance a reviewer needs to accept or reject an edge.
Skolem IRIs follow the RDF 1.1 / Wikidata convention: <https://w3id.org/nef/.well-known/genid/<hash>> — stable per
(source revision, sentence, target span), so re-running gives the same node.
"""
import hashlib

PREFIXES = """@prefix wd:   <http://www.wikidata.org/entity/> .
@prefix wdt:  <http://www.wikidata.org/prop/direct/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix nef:  <https://w3id.org/nef/anon#> .
@prefix gen:  <https://w3id.org/nef/.well-known/genid/> .
"""
STATUS = {"MISSING": "Missing", "AMBIGUOUS": "Ambiguous", "TEXT_UNKNOWN": "TextUnknown", "UNRESOLVED": "Unresolved",
          "UNKNOWN_VALUE": "KBUnknownValue", "NOT-DETECTED": None}


def lit(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"@en'


def skolem(*parts):
    return "gen:" + hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:16]


def write_item(out, it):
    """it: item_id, anchor_qid, props (list), outcome, answers (list), span, anchor_label, gender, tier, revision_url,
    slice_sha, method, candidates (list)."""
    if it["outcome"] == "NOT-DETECTED" or not it.get("anchor_qid") or not it.get("props"):
        return 0
    s = f"wd:{it['anchor_qid']}"; p = f"wdt:{it['props'][0]}"
    if it["outcome"] == "GROUNDED":
        o = f"wd:{it['answers'][0]}"
        out.append(f"{s} {p} {o} .")
    else:
        o = skolem(it["revision_url"], it["item_id"], it["span"])
        status = STATUS.get(it["outcome"], "Unresolved")
        cands = "".join(f" ;\n    nef:candidate wd:{c}" for c in it.get("candidates", []))
        gender = f' ;\n    nef:gender "{it["gender"]}"' if it.get("gender") else ""
        out.append(f"{s} {p} {o} .\n{o} a nef:AnonymousEntity ;\n    nef:status nef:{status} ;\n    nef:describedAs {lit(it['span'])} ;\n"
                   f"    rdfs:label {lit(it['span'] + ' (of ' + it['anchor_label'] + ')')} ;\n    nef:anchor {s} ;\n"
                   f"    nef:path \"{'/'.join(it['props'])}\"{gender}{cands} .")
    a = skolem("assertion", it["revision_url"], it["item_id"])
    tier = f' ;\n    nef:groundingTier "{it["tier"]}"' if it["outcome"] == "GROUNDED" and it.get("tier") else ""
    out.append(f"{a} a nef:Assertion ;\n    nef:subject {s} ;\n    nef:predicate {p} ;\n    nef:object {o} ;\n"
               f"    nef:outcome \"{it['outcome']}\"{tier} ;\n    prov:wasDerivedFrom <{it['revision_url']}> ;\n"
               f"    nef:kbEvidenceSlice \"{it['slice_sha']}\" ;\n    nef:method \"{it['method']}\" .")
    return 1


def serialize(items):
    out = [PREFIXES]
    n = sum(write_item(out, it) for it in items)
    return "\n\n".join(out) + "\n", n
