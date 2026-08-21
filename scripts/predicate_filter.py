#!/usr/bin/env python3
"""
PREDICATE VALIDITY — reject predicates that are not real DBpedia properties.

Scope note, measured rather than assumed: only 6% of the distinct predicates in
pilot 3 (14 of 227) are not real dbo properties, covering 3.4% of triples. The
long tail is mostly LEGITIMATE — `composer`, `largestCity`, `scientificName`
and `academicAdvisor` are all real and correctly applied. Open-domain extraction
should have a long predicate tail; that tail is not the defect.

What this removes is the genuinely invalid slice: hallucinated properties
(`numberOfUseOfProperty`, `medicalDiagnosis`) and non-English ontology labels
that leak in from ranking over the full property set (`مصنف`, `فنکار`). Small
in count, disproportionate in an audit — a reviewer who sees an Urdu predicate
stops trusting the rest of the sample.
"""
import json, os

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "..", "data", "valid_dbo_properties.json")


def load_valid(sparql_fn, refresh=False):
    """Every rdf:Property under the dbo namespace, cached to disk."""
    path = os.path.abspath(CACHE)
    if os.path.exists(path) and not refresh:
        return set(json.load(open(path)))
    q = ("SELECT DISTINCT ?p WHERE { ?p a "
         "<http://www.w3.org/1999/02/22-rdf-syntax-ns#Property> . "
         'FILTER(STRSTARTS(STR(?p), "http://dbpedia.org/ontology/")) }')
    props = {b["p"]["value"].rsplit("/", 1)[-1]
             for b in sparql_fn(q)["results"]["bindings"]}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(sorted(props), open(path, "w"))
    return props


def is_valid(rel, valid):
    """ASCII-only and present in the ontology.

    The ASCII test is not redundant: a non-English label can be a real property
    IRI, and we want it gone regardless, because the emitted graph is English."""
    if not rel or any(ord(c) > 127 for c in rel):
        return False
    return rel in valid
