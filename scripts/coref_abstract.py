#!/usr/bin/env python3
"""
ABSTRACT-LEVEL COREFERENCE — supply the antecedent Node 0 cannot see.

The problem
-----------
Node 0 resolves references *within* a sentence. An abstract is a discourse:

    "William Macomb was a merchant and politician."
    "He was born in Ireland in 1748."

Sentence 2, read alone, has no antecedent for "He". The pipeline linked it to
the nearest surface-form match — `dbr:He`, the chemical element helium — and
STRICT_URI_MODE waved it through, because helium is a perfectly real entity.
19.8% of the pilot's triples had a pronoun or generic noun as subject
(`IT` x30, `He` x27), the single largest quality defect measured.

The fix
-------
When the input is an abstract we already know what it is about: the abstract's
own URI. That is the antecedent. This module substitutes it before extraction,
so every downstream stage — linking, typing, the judge — sees the real entity
rather than a pronoun.

Two guards keep the substitution honest:

* TYPE AGREEMENT. `He`/`She` are only replaced when the abstract entity is a
  dbo:Person; `It`/`They` only when it is not. An abstract about a bridge that
  says "He" is talking about someone else, and is left alone.
* SENTENCE-INITIAL ONLY. A mid-sentence pronoun frequently refers to a local
  antecedent introduced earlier in that same sentence, which Node 0 already
  handles correctly. Rewriting those would break working behaviour.

Every substitution is logged and counted, so the audit measures how often this
is wrong instead of assuming it is right.
"""
import re

# Pronouns that survive to emission as real-but-wrong DBpedia URIs.
# (`He` -> helium, `It` -> information technology, `They` -> a 2002 film.)
PERSON_SUBJ = {"He", "She"}
PERSON_POSS = {"His", "Her"}
THING_SUBJ = {"It", "They"}
THING_POSS = {"Its", "Their"}

# Local names that must never appear as a subject or object. Remapped to the
# abstract entity where possible, dropped otherwise.
BAD_LOCALS = {
    "He", "She", "It", "They", "Him", "Her", "Them", "His", "Its", "Their",
    "I", "We", "You", "Me", "Us", "IT", "THEY", "HE", "SHE",
    "This", "That", "These", "Those", "One", "User", "Users",
    "Who", "Which", "There", "Here",
}


def entity_label(uri):
    """`.../William_Macomb_(merchant)` -> `William Macomb` (readable form)."""
    local = uri.rsplit("/", 1)[-1]
    return re.sub(r"\s*\([^)]*\)\s*$", "", local.replace("_", " ")).strip()


def entity_local(uri):
    """`.../William_Macomb_(merchant)` -> `William_Macomb_(merchant)` (URI form)."""
    return uri.rsplit("/", 1)[-1]


def is_person(uri, sparql_fn, _cache={}):
    """One cheap ASK per abstract against the local store, memoised."""
    if uri in _cache:
        return _cache[uri]
    q = (f'ASK {{ <{uri}> a ?t . '
         f'VALUES ?t {{ <http://dbpedia.org/ontology/Person> '
         f'<http://xmlns.com/foaf/0.1/Person> }} }}')
    try:
        val = bool(sparql_fn(q).get("boolean"))
    except Exception:
        val = None                      # unknown: substitution is skipped
    _cache[uri] = val
    return val


def rewrite(sentence, uri, person, stats=None):
    """Replace a sentence-initial pronoun with the abstract's entity.

    Returns the sentence unchanged when the pronoun disagrees in type with the
    entity, or when the entity's type could not be determined."""
    if person is None:
        return sentence
    label = entity_label(uri)
    if not label:
        return sentence

    m = re.match(r"^(\w+)\b", sentence)
    if not m:
        return sentence
    head = m.group(1)

    if person and head in PERSON_SUBJ:
        rep = label
    elif person and head in PERSON_POSS:
        rep = label + "'s"
    elif (not person) and head in THING_SUBJ:
        rep = label
    elif (not person) and head in THING_POSS:
        rep = label + "'s"
    else:
        return sentence

    if stats is not None:
        stats[head] = stats.get(head, 0) + 1
    return rep + sentence[len(head):]


def repair_term(term, uri, person):
    """Emission-time net for pronouns the rewrite did not catch.

    Returns the abstract entity's local name when the term is a bad local and
    the type agrees, None when the triple should be dropped, or the term
    unchanged when it is fine."""
    if term not in BAD_LOCALS:
        return term
    if person is None:
        return None
    if person and term in {"It", "IT", "Its", "They", "Their", "Them"}:
        return None                     # thing-pronoun in a person abstract
    if (not person) and term in {"He", "HE", "She", "SHE", "His", "Her", "Him"}:
        return None                     # person-pronoun in a thing abstract
    if term in {"User", "Users", "This", "That", "These", "Those", "One",
                "Who", "Which", "There", "Here", "I", "We", "You", "Me", "Us"}:
        return None                     # not coreferential to the abstract
    return entity_local(uri)


# ── TIER 2: partial-name mentions ────────────────────────────────────────────
# Pilot 3 found 5 sentences whose candidates all died because the subject was a
# surname the linker could not resolve: "Libbrecht received a B.S. in physics at
# Caltech" in an abstract about `Kenneth G. Libbrecht`.
#
# SENTENCE-INITIAL ONLY, and for PERSON abstracts only. Both restrictions are
# load-bearing. Mid-sentence replacement mangles the common introduction form —
# `Hyman "Hy" Peskin (November 5, 1915...)` would become `Hyman "Hy" Hy Peskin`
# — because those sentences already contain a fuller version of the name. And
# without the person test, an abstract titled `List of cities in Japan` would
# capture every mention of `Japan`.
import re as _re


def resolve_partial_name(sentence, uri, person, stats=None):
    if not person:
        return sentence
    label = entity_label(uri)
    parts = _re.findall(r"[A-Z][a-z]{2,}", label)
    if len(parts) < 2:
        return sentence                     # single-token label: nothing partial
    m = _re.match(r"^([A-Z][a-z]{2,})\b", sentence)
    if not m or m.group(1) not in parts:
        return sentence
    if label in sentence:
        return sentence                     # full name already present
    if stats is not None:
        stats["partial_name"] = stats.get("partial_name", 0) + 1
    return label + sentence[len(m.group(1)):]
