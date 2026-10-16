"""DBpedia KBQuery over the local oxigraph store (DBpedia 2022-12 snapshot, read-only, :7878).
Same interface as kb_wikidata.WikidataKB so the decision code never sees which KB it talks to.

Capabilities differ and are declared, never faked:
- no gender data in this snapshot (foaf:gender not loaded) -> gender filters are skipped and
  every answer carries gender_checked=False;
- no redirect table -> titles map to IRIs by underscoring only;
- schema-uniqueness comes from owl:FunctionalProperty in data/dbpedia.owl (31 properties, none of
  the object relations we use), so DBpedia groundings are always data-unique.
"""
import hashlib, json, os, re, time, requests
from urllib.parse import quote

DBO = "http://dbpedia.org/ontology/"
DBR = "http://dbpedia.org/resource/"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
CONTAINMENT = ["isPartOf", "country", "state", "region", "locatedInArea", "department", "county",
               "province", "district", "federalState", "subdivision", "parentOrganisation"]
OWL = os.path.join(os.path.dirname(__file__), "../../../data/dbpedia.owl")


class KBUnavailable(RuntimeError):
    pass


class DBpediaKB:
    name = "dbpedia"
    supports = {"gender": False, "qualifiers": False, "redirects": False, "unknown_values": False}

    def __init__(self, endpoint="http://localhost:7878/query", cache_dir=None, tries=3):
        self.endpoint, self.tries = endpoint, tries
        self.cache_dir = cache_dir or os.path.join(os.path.dirname(__file__), "cache_dbpedia")
        os.makedirs(self.cache_dir, exist_ok=True)
        self._functional = None

    def sparql(self, query):
        f = os.path.join(self.cache_dir, hashlib.sha1((self.endpoint + "\n" + query).encode()).hexdigest() + ".json")
        if os.path.exists(f):
            return json.load(open(f))
        last = None
        for i in range(self.tries):
            try:
                r = requests.post(self.endpoint, data={"query": query}, timeout=120,
                                  headers={"Accept": "application/sparql-results+json"})
                if r.status_code == 200:
                    j = r.json(); out = j.get("boolean", j.get("results", {}).get("bindings"))
                    json.dump(out, open(f, "w")); return out
                last = f"{r.status_code} {r.text[:120]}"
            except requests.RequestException as e:
                last = str(e)
            time.sleep(2 * (i + 1))
        raise KBUnavailable(f"local DBpedia store: {last} (is the nef-oxigraph container up?)")

    # ---------- entities ----------
    @staticmethod
    def iri(local):
        return DBR + local if not local.startswith("http") else local

    @staticmethod
    def local(iri):
        return iri[len(DBR):] if iri.startswith(DBR) else iri

    def id_for_title(self, title):
        local = title.replace(" ", "_")
        ok = self.sparql(f"ASK {{ <{DBR}{local}> ?p ?o }}")
        return local if ok else None

    def labels(self, ids, langs=("en",)):
        out = {}
        for i in ids:
            rows = self.sparql(f'SELECT ?l WHERE {{ <{self.iri(i)}> <{RDFS_LABEL}> ?l FILTER(LANG(?l) = "{langs[0]}") }} LIMIT 1')
            out[i] = rows[0]["l"]["value"] if rows else i.replace("_", " ")
        return out

    def popularity(self, local):
        rows = self.sparql(f"SELECT (COUNT(?s) AS ?n) WHERE {{ ?s <{DBO}wikiPageWikiLink> <{self.iri(local)}> }}")
        return int(rows[0]["n"]["value"]) if rows else 0

    # ---------- facts ----------
    @staticmethod
    def _path(hops):
        parts = []
        for h in hops:
            alt = "|".join(f"<{DBO}{p}>" for p in h.props)
            alt = f"({alt})" if len(h.props) > 1 else alt
            parts.append(("^" if h.dir == "in" else "") + alt)
        return "/".join(parts)

    def values(self, anchor, alternatives, gender=None, mask=()):
        unions = " UNION ".join(f"{{ <{self.iri(anchor)}> {self._path(p)} ?x }}" for p in alternatives)
        rows = self.sparql(f"SELECT DISTINCT ?x WHERE {{ {unions} FILTER(isIRI(?x)) }}")
        known = sorted({self.local(r["x"]["value"]) for r in rows if r["x"]["value"].startswith(DBR)} - set(mask))
        return {"known": known, "unknown_values": 0, "gender_checked": gender is None}

    def has_any(self, anchor, prop):
        return bool(self.sparql(f"ASK {{ <{self.iri(anchor)}> <{DBO}{prop}> ?x }}"))

    def ancestors(self, local, props=CONTAINMENT):
        alt = "|".join(f"<{DBO}{p}>" for p in props)
        rows = self.sparql(f"SELECT DISTINCT ?b WHERE {{ <{self.iri(local)}> ({alt})+ ?b }}")
        return {self.local(r["b"]["value"]) for r in rows}

    def single_value_props(self, props):
        if self._functional is None:
            owl = open(OWL).read()
            self._functional = set(re.findall(
                r'rdf:about="http://dbpedia.org/ontology/([^"]+)">\s*<rdf:type rdf:resource="http://www.w3.org/2002/07/owl#FunctionalProperty"', owl))
        return set(props) & self._functional

    def schema_unique(self, alternatives):
        if len(alternatives) != 1 or any(len(h.props) != 1 for h in alternatives[0]):
            return False
        props = [h.props[0] for h in alternatives[0]]
        return set(props) <= self.single_value_props(props)
