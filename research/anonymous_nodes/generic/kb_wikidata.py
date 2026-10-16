"""Wikidata KBQuery (METHODOLOGY.md §3.4) — the lessons of 9–16 Oct as reusable code.

- QLever primary, WDQS fallback; POST; a User-Agent; backoff on 429/5xx.
- Transitive paths only from a BOUND subject (VALUES on both ends times out on QLever).
- Every response cached on disk (sha1 of endpoint + query), so reruns don't hit the service.
- A failed query raises KBUnavailable — it is never returned as an empty answer.
- Unknown values (/.well-known/genid/) are counted separately, never returned as answers.
"""
import hashlib, json, os, time, requests
from .ir import Hop

WD = "http://www.wikidata.org/entity/"
WDT = "http://www.wikidata.org/prop/direct/"
P = "http://www.wikidata.org/prop/"
PS = "http://www.wikidata.org/prop/statement/"
GENDER_QID = {"male": "Q6581097", "female": "Q6581072"}
SINGLE_VALUE = {"Q19474404", "Q52060874"}           # single-value, single-best-value constraints
CONTAINMENT = ["P131", "P17", "P361", "P276", "P706", "P749"]
UA = "nef-research/0.1 (https://github.com/NakulSingh156/dbpedia-neuro-symbolic-extraction; research script)"


class KBUnavailable(RuntimeError):
    pass


class WikidataKB:
    name = "wikidata"

    def __init__(self, cache_dir=None, endpoints=("https://qlever.dev/api/wikidata", "https://query.wikidata.org/sparql"),
                 pause=1.0, tries=5):
        self.endpoints, self.pause, self.tries = endpoints, pause, tries
        self.cache_dir = cache_dir or os.path.join(os.path.dirname(__file__), "cache_wikidata")
        os.makedirs(self.cache_dir, exist_ok=True)
        self._last = 0.0

    # ---------- transport ----------
    def _cache(self, key):
        return os.path.join(self.cache_dir, hashlib.sha1(key.encode()).hexdigest() + ".json")

    def sparql(self, query):
        for ep in self.endpoints:
            f = self._cache(ep + "\n" + query)
            if os.path.exists(f):
                return json.load(open(f))
        last = None
        for ep in self.endpoints:
            for i in range(self.tries):
                wait = self.pause - (time.time() - self._last)
                if wait > 0: time.sleep(wait)
                self._last = time.time()
                try:
                    r = requests.post(ep, data={"query": query}, timeout=120,
                                      headers={"User-Agent": UA, "Accept": "application/sparql-results+json"})
                except requests.RequestException as e:
                    last = str(e); time.sleep(3 * 2 ** i); continue
                if r.status_code == 200:
                    j = r.json(); out = j.get("boolean", j.get("results", {}).get("bindings"))
                    json.dump(out, open(self._cache(ep + "\n" + query), "w"))
                    return out
                last = f"{r.status_code} {r.text[:120]}"
                if r.status_code in (429, 500, 502, 503, 504):
                    time.sleep(min(60, 3 * 2 ** i)); continue
                break                                   # 4xx other than 429: try the next endpoint
        raise KBUnavailable(last)

    def api(self, url, params):
        f = self._cache(url + json.dumps(params, sort_keys=True))
        if os.path.exists(f):
            return json.load(open(f))
        for i in range(self.tries):
            r = requests.get(url, params={**params, "format": "json"}, headers={"User-Agent": UA}, timeout=60)
            if r.status_code == 200 and r.text.startswith("{"):
                j = r.json(); json.dump(j, open(f, "w")); time.sleep(0.5); return j
            time.sleep(min(60, 5 * 2 ** i))
        raise KBUnavailable(f"{url} {r.status_code}")

    # ---------- entities ----------
    def qid_for_title(self, title, wiki="en"):
        j = self.api(f"https://{wiki}.wikipedia.org/w/api.php", {"action": "query", "prop": "pageprops",
                     "ppprop": "wikibase_item", "redirects": 1, "titles": title})
        page = next(iter(j["query"]["pages"].values()))
        return page.get("pageprops", {}).get("wikibase_item")

    def labels(self, qids, langs=("en", "mul")):
        """Best label per QID: preferred languages first, else any language (秋月種美 has no English label)."""
        out = {}
        qids = [q for q in qids if q]
        for i in range(0, len(qids), 50):
            j = self.api("https://www.wikidata.org/w/api.php", {"action": "wbgetentities",
                         "ids": "|".join(qids[i:i + 50]), "props": "labels"})
            for q, e in j.get("entities", {}).items():
                labs = e.get("labels", {})
                pick = next((labs[l]["value"] for l in langs if l in labs), None)
                out[q] = pick or (next(iter(labs.values()))["value"] if labs else q)
        return out

    def popularity(self, qid):
        rows = self.sparql(f"SELECT ?n WHERE {{ <{WD}{qid}> <http://wikiba.se/ontology#sitelinks> ?n }}")
        return int(rows[0]["n"]["value"]) if rows else 0

    # ---------- facts ----------
    @staticmethod
    def _path(hops):
        parts = []
        for h in hops:
            alt = "|".join(f"<{WDT}{p}>" for p in h.props)
            alt = f"({alt})" if len(h.props) > 1 else alt
            parts.append(("^" if h.dir == "in" else "") + alt)
        return "/".join(parts)

    def values(self, anchor_qid, alternatives, gender=None, mask=()):
        """Answers for anchor + any of the alternative paths, after a lenient gender filter
        (drop values whose recorded gender is the opposite; keep values with no gender).
        `mask` = answer QIDs to hide, simulating a deleted fact (GrailQAbility-style MISSING items)."""
        unions = " UNION ".join(f"{{ <{WD}{anchor_qid}> {self._path(p)} ?x }}" for p in alternatives)
        other = {"male": "female", "female": "male"}.get(gender)
        flt = f"FILTER NOT EXISTS {{ ?x <{WDT}P21> <{WD}{GENDER_QID[other]}> }}" if other else ""
        rows = self.sparql(f"SELECT DISTINCT ?x WHERE {{ {unions} {flt} }}")
        vals = [r["x"]["value"] for r in rows]
        known = sorted({v.rsplit("/", 1)[1] for v in vals if v.startswith(WD + "Q")} - set(mask))
        unknown = sum(1 for v in vals if "/.well-known/genid/" in v)
        return {"known": known, "unknown_values": unknown}

    def has_any(self, anchor_qid, prop):
        return bool(self.sparql(f"ASK {{ <{WD}{anchor_qid}> <{WDT}{prop}> ?x }}"))

    def ancestors(self, qid, props=CONTAINMENT):
        alt = "|".join(f"<{WDT}{p}>" for p in props)
        rows = self.sparql(f"SELECT DISTINCT ?b WHERE {{ <{WD}{qid}> ({alt})+ ?b }}")
        return {r["b"]["value"].rsplit("/", 1)[1] for r in rows}

    def single_value_props(self, props):
        vals = " ".join(f"<{WD}{p}>" for p in props)
        rows = self.sparql(f"""SELECT ?p ?c WHERE {{ VALUES ?p {{ {vals} }}
            ?p <{P}P2302> ?st . ?st <{PS}P2302> ?c }}""")
        return {r["p"]["value"].rsplit("/", 1)[1] for r in rows if r["c"]["value"].rsplit("/", 1)[1] in SINGLE_VALUE}

    def schema_unique(self, alternatives):
        """True only when there is one path and every hop is a single property with a single-value constraint."""
        if len(alternatives) != 1 or any(len(h.props) != 1 for h in alternatives[0]):
            return False
        props = [h.props[0] for h in alternatives[0]]
        return set(props) <= self.single_value_props(props)
