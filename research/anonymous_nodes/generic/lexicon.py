"""Load relation_lexicon.json and expand a relation chain into KB paths (M3, lexicon step)."""
import json, os
from .ir import Hop

_LEX = None
SYNONYMS = {"brothers": "brother", "sisters": "sister", "sons": "son", "daughters": "daughter", "children": "child",
            "nephews": "nephew", "nieces": "niece", "parents": "parent", "wives": "wife", "husbands": "husband",
            "founders": "founder", "members": "member", "queen": "wife", "king": "husband", "widow": "wife",
            "widower": "husband", "partner": "spouse", "headquarter": "headquarters", "co-founder": "founder",
            "kids": "child", "kid": "child", "uncles": "uncle", "aunts": "aunt", "cousins": "cousin",
            "grandsons": "grandson", "granddaughters": "granddaughter", "grandchildren": "grandchild"}


def lexicon():
    global _LEX
    if _LEX is None:
        _LEX = json.load(open(os.path.join(os.path.dirname(__file__), "relation_lexicon.json")))
    return _LEX


def entry(noun):
    n = noun.lower().strip()
    n = SYNONYMS.get(n, n)
    return lexicon().get(n)


def expand(chain, kb):
    """chain = relation nouns from the anchor outward, e.g. ["founder", "grandson"].
    Returns (alternative paths as list[list[Hop]], gender of the final noun) or (None, None)."""
    if not chain:
        return None, None            # an empty chain is not a path (it slipped through keep() before 17 Oct)
    alts, gender = [[]], None
    for noun in chain:
        e = entry(noun)
        if not e or not e.get(kb):
            return None, None
        alts = [a + [Hop(props=h) for h in p] for a in alts for p in e[kb]]
        gender = e.get("gender")
    return alts, gender
