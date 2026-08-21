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


# ── TIER 3: definite descriptions ────────────────────────────────────────────
# "The road begins at FM 1573 in Gruver" in an abstract about FM 2018 links the
# subject to `dbr:The_Road` — the Cormac McCarthy novel. Measured at 5.1% of
# triples in the 2,000-abstract run, and more damaging than an unlinkable
# subject: it is a well-formed statement attached to a real, unrelated entity.
# STRICT_URI_MODE cannot catch it, because `The_Road` genuinely exists.
#
# Unlike pronouns, definite descriptions are an OPEN set, so the trigger is
# structural (sentence-initial "The|A|An" + common noun) and the safety comes
# from classifying the head noun into three groups:
#
#   ATTRIBUTE   "the wingspan", "the population" — a property of the abstract
#               entity. The subject still resolves TO that entity: "The wingspan
#               is 20 mm" means `<moth> wingspan "20 mm"`. Safe to remap.
#   ENTITY      "the film", "the village" — the entity itself, confirmed by
#               matching the head noun against the entity's own type labels
#               (with a synonym layer, since DBpedia types `film` as `movie`).
#   AGENT       "the director", "the author" — a DIFFERENT entity related to the
#               subject. Never remap; that would assert the film directed itself.
#
# Anything unclassified is left alone. Coverage is deliberately traded for
# precision: a missed rewrite costs one triple, a wrong one corrupts an entity.

_DEFN = _re.compile(r"^(?:The|A|An)\s+([a-z]+)\b")

# Properties/parts of the entity — the entity remains the correct subject.
ATTRIBUTE_HEADS = {
    "population", "area", "wingspan", "forewings", "hindwings", "larvae",
    "length", "height", "width", "depth", "elevation", "altitude", "name",
    "genus", "species", "family", "climate", "economy", "history", "design",
    "surface", "interior", "exterior", "structure", "building", "site",
    "population", "census", "terrain", "summit", "mouth", "source", "route",
}

# A different entity that merely appears in the abstract. Never coreferential.
AGENT_HEADS = {
    "director", "author", "founder", "president", "singer", "player", "writer",
    "owner", "manager", "coach", "artist", "producer", "composer", "editor",
    "architect", "designer", "developer", "publisher", "winner", "leader",
    "chairman", "governor", "mayor", "captain", "pilot", "driver", "actor",
    "son", "daughter", "father", "mother", "brother", "sister", "wife",
    "husband",
}
# NOTE: "team", "company", "family", "district" are deliberately NOT listed
# above. In an abstract about a football club, "The team won the league" IS
# coreferential; in an abstract about a player it is not. The type check
# decides, which is exactly the discrimination AGENT_HEADS cannot make.

# DBpedia's class labels do not match everyday head nouns. Curated from the
# misses measured on the 2,000-abstract run (58x "film" vs "movie" alone).
TYPE_SYNONYMS = {
    "film": {"movie", "work"}, "movie": {"film", "work"},
    "song": {"musical work", "single"}, "album": {"musical work", "album"},
    "book": {"written work", "book"}, "novel": {"written work", "book"},
    "village": {"populated place", "settlement", "place"},
    "town": {"populated place", "settlement", "place"},
    "city": {"populated place", "settlement", "place", "city"},
    "community": {"populated place", "settlement", "place"},
    "road": {"road", "route", "infrastructure"},
    "line": {"railway line", "route", "infrastructure"},
    "station": {"station", "infrastructure", "architectural structure"},
    "school": {"educational institution", "school", "organisation"},
    "college": {"educational institution", "organisation"},
    "vehicle": {"mean of transportation", "spacecraft", "aircraft", "rocket"},
    "aircraft": {"mean of transportation", "aircraft"},
    "match": {"sports event", "football match", "event"},
    "series": {"work", "television show"}, "magazine": {"periodical literature", "work"},
    "newspaper": {"newspaper", "periodical literature", "work"},
    "facility": {"building", "architectural structure", "place"},
    "museum": {"museum", "building", "architectural structure"},
    "tree": {"plant", "eukaryote", "species"},
    "moth": {"insect", "animal", "eukaryote"},
    "team": {"sports team", "soccer club", "organisation", "club"},
    "club": {"sports team", "soccer club", "organisation", "club"},
    "company": {"company", "organisation", "business"},
    "band": {"band", "musical artist", "organisation", "group"},
    "district": {"populated place", "place", "administrative region"},
    "region": {"populated place", "place", "administrative region"},
    "tournament": {"sports event", "event", "competition"},
    "event": {"sports event", "event", "competition"},
    "centre": {"building", "architectural structure", "place"},
    "center": {"building", "architectural structure", "place"},
    "church": {"church", "building", "religious building"},
    "river": {"river", "stream", "body of water", "natural place"},
    "island": {"island", "place", "natural place"},
    "mountain": {"mountain", "natural place", "place"},
    "airport": {"airport", "infrastructure"},
    "park": {"park", "protected area", "place"},
    "bridge": {"bridge", "architectural structure", "infrastructure"},
    "game": {"video game", "game", "software", "work"},
    "university": {"university", "educational institution", "organisation"},
    "hotel": {"hotel", "building", "architectural structure"},
    "family": {"family", "eukaryote", "species"},
}


def resolve_definite(sentence, uri, type_labels, stats=None):
    """Replace a sentence-initial definite description with the abstract entity.

    `type_labels` is the lowercased set of rdfs:label values of the entity's
    dbo types (e.g. {"movie", "work"}). Pass an empty set when unknown — the
    ENTITY branch is then skipped, ATTRIBUTE still applies."""
    m = _DEFN.match(sentence)
    if not m:
        return sentence
    head = m.group(1)
    if head in AGENT_HEADS:
        return sentence                       # a different entity: never touch
    label = entity_label(uri)
    if not label or label.lower().startswith(head):
        return sentence

    kind = None
    if head in ATTRIBUTE_HEADS:
        kind = "attribute"
    else:
        want = TYPE_SYNONYMS.get(head, set()) | {head}
        if any(w in L or L in w for L in type_labels for w in want):
            kind = "entity"
    if kind is None:
        return sentence

    if stats is not None:
        stats[f"definite_{kind}"] = stats.get(f"definite_{kind}", 0) + 1
    # "The film was released..." -> "<Entity> was released..."
    return label + sentence[m.end():]


def type_labels(uri, sparql_fn, _cache={}):
    """Lowercased rdfs:label of every dbo type the entity has. One query per
    abstract, memoised — same cost profile as is_person()."""
    if uri in _cache:
        return _cache[uri]
    q = (f'SELECT ?l WHERE {{ <{uri}> a ?t . '
         f'?t <http://www.w3.org/2000/01/rdf-schema#label> ?l . '
         f'FILTER(STRSTARTS(STR(?t), "http://dbpedia.org/ontology/")) '
         f'FILTER(lang(?l) = "en") }}')
    try:
        out = {b["l"]["value"].lower()
               for b in sparql_fn(q)["results"]["bindings"]}
    except Exception:
        out = set()
    _cache[uri] = out
    return out
