"""M5 — convention-aware answer comparison (METHODOLOGY.md §3.3; finding 5).

Two QIDs count as the same answer when one reaches the other through a "convention" relation:
  containment   P131/P17/P361/P276/P706/P749 (transitive)        town vs county
  subclass      P279 (transitive), either direction               author vs writer, IDM vs electronic
  nationality   P17 / P27 / P495 of a demonym or people item      "Americans" vs United States
  sport/field   P641 or P425 of an occupation, then subclass      "football player" vs association football
  demonym       the text string is a demonym (P1549) of the answer "American" vs United States — matched on the
                LABEL, because such strings often link to disambiguation pages (Q4167410), not to a people item
  succession    P1366 / P1365 (transitive)                        historical polity vs its successor
Each rule is data (RULES); every merge reports the rule that fired, so false merges can be audited.
"""
from .kb_wikidata import WikidataKB, WD, WDT

RULES = {
    "containment": ("strict", None),        # kb.ancestors(strict=True), see kb_wikidata.CONT_FIRST/CONT_REST
    "subclass":    (["P279"], True),
    "nationality": (["P17", "P27", "P495"], False),
    "sport":       (["P641", "P425"], "then_subclass"),
    "succession":  (["P1366", "P1365"], True),
}


class Comparator:
    def __init__(self, kb=None, rules=RULES):
        self.kb, self.rules = kb or WikidataKB(), rules
        self._reach = {}

    def reach(self, q):
        """{rule: set of QIDs reachable from q under that rule} — one cached query per rule."""
        if q not in self._reach:
            out = {}
            for name, (props, transitive) in self.rules.items():
                if props == "strict":
                    out[name] = self.kb.ancestors(q, strict=True); continue
                alt = "|".join(f"<{WDT}{p}>" for p in props)
                if transitive == "then_subclass":
                    path = f"({alt})/<{WDT}P279>*"
                else:
                    path = f"({alt})+" if transitive else (f"({alt})" if len(props) > 1 else alt)
                rows = self.kb.sparql(f"SELECT DISTINCT ?b WHERE {{ <{WD}{q}> {path} ?b }}")
                out[name] = {r["b"]["value"].rsplit("/", 1)[1] for r in rows}
            self._reach[q] = out
        return self._reach[q]

    def demonyms(self, q):
        rows = self.kb.sparql(f'SELECT ?d WHERE {{ <{WD}{q}> <{WDT}P1549> ?d FILTER(LANG(?d) = "en") }}')
        return {r["d"]["value"].lower() for r in rows}

    def is_disambiguation(self, q):
        return bool(self.kb.sparql(f"ASK {{ <{WD}{q}> <{WDT}P31> <{WD}Q4167410> }}"))

    def same(self, a, b, a_text=None, b_text=None):
        """(True, rule) if a and b are the same answer up to conventions, else (False, None).
        a_text / b_text: the surface strings, used by the demonym rule (looked up as labels if absent)."""
        if a == b:
            return True, "identical"
        ra, rb = self.reach(a), self.reach(b)
        for name in self.rules:
            if b in ra[name] or a in rb[name]:
                return True, name
        # sport/field: the occupation's DIRECT sport/field is a superclass of the answer ("football" ⊇ association
        # football). Only the direct field counts: sharing a distant ancestor ("occupation") merged farmer with
        # politician in the first version (16 Oct).
        fa, fb = self.fields(a), self.fields(b)
        if fa & (rb["subclass"] | {b}) or fb & (ra["subclass"] | {a}):
            return True, "sport_family"
        labels = self.kb.labels([a, b])
        ta, tb = (a_text or labels.get(a, "")).lower(), (b_text or labels.get(b, "")).lower()
        if ta and ta == tb:
            return True, "same_label"            # e.g. both sides linked to the same-named disambiguation page
        if ta in self.demonyms(b) or tb in self.demonyms(a):
            return True, "demonym"
        # demonym of a place that lies inside the other answer ("Scottish" -> Scotland -> United Kingdom)
        for t, other in ((ta, b), (tb, a)):
            for c in self.places_with_demonym(t):
                if c == other or other in self.kb.ancestors(c):
                    return True, "demonym_containment"
        return False, None

    def fields(self, q):
        rows = self.kb.sparql(f"SELECT DISTINCT ?f WHERE {{ <{WD}{q}> <{WDT}P641>|<{WDT}P425> ?f }}")
        return {r["f"]["value"].rsplit("/", 1)[1] for r in rows}

    # only countries, sovereign states, constituent countries (Scotland) and historical countries count as
    # demonym places: an unrestricted lookup found a "Russian"-demonym item inside France (16 Oct)
    DEMONYM_PLACE_TYPES = ("Q6256", "Q3624078", "Q3336843", "Q3024240")

    def places_with_demonym(self, text):
        if not text or len(text) > 40:
            return set()
        lit = text.replace('"', "")
        types = " ".join(f"<{WD}{t}>" for t in self.DEMONYM_PLACE_TYPES)
        rows = self.kb.sparql(f"""SELECT DISTINCT ?c WHERE {{ VALUES ?ty {{ {types} }} ?c <{WDT}P31> ?ty .
            ?c <{WDT}P1549> ?d FILTER(LANG(?d) = "en" && LCASE(STR(?d)) = "{lit}") }} LIMIT 20""")
        return {r["c"]["value"].rsplit("/", 1)[1] for r in rows}
