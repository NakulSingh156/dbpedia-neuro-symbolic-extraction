#!/usr/bin/env python3
"""
WIKIDATA SURVEY — is the 23% coverage ceiling DBpedia's limit, or the method's?

The DBpedia survey (../survey_uniqueness.py, ../coverage.py) found that when
DBpedia has a relation it usually points to one entity (77% unique up to
containment), but DBpedia has the relation for only 23% of the facts our
pipeline extracts, so only ~17% of descriptions could be grounded. If Wikidata
covers far more, the bottleneck is the KB and the method should go multi-KB.

Two parts.

PART A — population uniqueness, EXACT (no sampling on the Wikidata side).
  Population = Wikidata items that have an English Wikipedia article, which is
  DBpedia's own universe, so the two KBs are compared on the same kind of
  entities. Per relation: share of anchors with exactly one value (forward and
  inverse), share unique up to one-hop containment (sampled multi-valued
  anchors, as in the DBpedia survey), and share with a Wikidata "unknown value"
  (stored as .well-known/genid skolem IRIs — Wikidata's native anonymous node).
  Values are any Wikidata item, with or without a Wikipedia article: an item
  without one is still a known identity.

PART B — paired, per fact. The headline.
  For the SAME relational facts our pipeline extracted from 2,000 Wikipedia
  abstracts (Phase 1), ask both KBs "subject's <relation> -> how many answers?".
  Same containment rule on both sides (transitive). When exactly one answer is
  left, check whether it is the entity the text actually named — a correctness
  signal the DBpedia-only survey did not have. Phase 1 is ~60% precise, which
  depresses that check equally for both KBs, so the comparison stays fair.
  Every name is mapped to a QID through the Wikipedia API (which resolves
  redirects), and identity is compared QID-to-QID on both sides.

Relation mapping: owl:equivalentProperty links from the DBpedia ontology, plus a
small manual set (MANUAL) for relations the ontology leaves unmapped, each with
its reason. Everything mapped manually is reported as such.

Needs: QLever's public Wikidata endpoint, and the local DBpedia oxigraph on :7878.
"""
import argparse, collections, json, os, random, statistics, sys, time, urllib.parse
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

ap = argparse.ArgumentParser()
ap.add_argument("--qlever", default="https://qlever.dev/api/wikidata")
ap.add_argument("--dbpedia", default="http://localhost:7878/query")
ap.add_argument("--min-freq", type=int, default=3)
ap.add_argument("--multi-sample", type=int, default=200, help="multi-valued anchors checked for containment (Part A)")
ap.add_argument("--multi-cap", type=int, default=300000)
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--pause", type=float, default=0.6, help="seconds between QLever calls (it rate-limits)")
ap.add_argument("--out", default=os.path.join(HERE, "results"))
ap.add_argument("--part", choices=["A", "B", "AB"], default="AB")
args = ap.parse_args()

UA = "NEF-research/0.1 (https://github.com/NakulSingh156; nakulsingh0910@gmail.com)"
WD = "http://www.wikidata.org/entity/"
WDT = "http://www.wikidata.org/prop/direct/"
GENID = "http://www.wikidata.org/.well-known/genid/"
DBO = "http://dbpedia.org/ontology/"
DBR = "http://dbpedia.org/resource/"
ENWIKI = "https://en.wikipedia.org/"
PFX = "PREFIX schema: <http://schema.org/>\n"

# Relations the ontology leaves unmapped but which matter by volume or are the
# paper's own example class. Each mapping is a judgement and is reported.
MANUAL = {
    "parent":     (["P22", "P25"], "Wikidata splits parent into father/mother; union = DBpedia's parent"),
    "relative":   (["P1038"], "relative"),
    "location":   (["P276", "P131"], "DBpedia location conflates 'located at' and 'in admin. entity'"),
    "sport":      (["P641"], "sport"),
    "profession": (["P106"], "DBpedia profession ~ Wikidata occupation"),
}
# Wikidata-only rows for Part A: tests the "father is clearer than parent" hypothesis.
EXTRA = {"father (P22)": ["P22"], "mother (P25)": ["P25"], "sibling (P3373)": ["P3373"]}

CONT_WD = ["P131", "P17", "P361", "P276", "P706", "P749"]
CONT_DBO = ["isPartOf", "country", "state", "region", "locatedInArea", "department", "county",
            "province", "district", "federalState", "subdivision", "parentOrganisation"]

KINSHIP = {"spouse", "child", "parent", "relative", "relation", "partner"}
PLACE = {"birthPlace", "deathPlace", "location", "country", "isPartOf", "locatedInArea", "city",
         "state", "region", "headquarter", "hometown", "foundationPlace", "nationality",
         "residence", "ground", "locationCountry", "county", "district", "province"}


# ── endpoints ───────────────────────────────────────────────────────────────
_last = [0.0]


def wq(query, tsv=False, tries=7):
    """QLever with a polite pause and backoff on 429/5xx. None = failed."""
    for i in range(tries):
        wait = args.pause - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            r = requests.post(args.qlever, data={"query": PFX + query},
                              headers={"User-Agent": UA,
                                       "Accept": "text/tab-separated-values" if tsv
                                       else "application/sparql-results+json"},
                              timeout=300)
            if r.status_code == 200:
                if tsv:
                    lines = r.text.strip().split("\n")[1:]
                    return [l.strip().strip("<>") for l in lines if l.strip()]
                return r.json()["results"]["bindings"]
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(min(60, 3 * 2 ** i))
                continue
            print(f"   QLever HTTP {r.status_code}: {r.text[:160]}", flush=True)
            return None
        except Exception as e:
            time.sleep(min(60, 3 * 2 ** i))
            last = e
    print(f"   QLever gave up after {tries} tries", flush=True)
    return None


def dq(query):
    try:
        r = requests.post(args.dbpedia, data={"query": query},
                          headers={"Accept": "application/sparql-results+json"}, timeout=300)
        r.raise_for_status()
        return r.json()["results"]["bindings"]
    except Exception as e:
        print(f"   DBpedia query failed: {str(e)[:120]}", flush=True)
        return None


def path(props):
    """`<P26>` or `<P22>|<P25>` — a SPARQL alternative path over truthy props."""
    return "|".join(f"<{WDT}{p}>" for p in props)


def qid_ok(o):
    return "FILTER(STRSTARTS(STR(%s), \"%s\"))" % (o, WD + "Q")


POP = "?__a schema:about ?s ; schema:isPartOf <%s> ." % ENWIKI


# ── mapping ─────────────────────────────────────────────────────────────────
def load_mapping():
    import rdflib
    g = rdflib.Graph()
    g.parse(os.path.join(ROOT, "data", "dbpedia.owl"))
    m = collections.defaultdict(set)
    for s, o in g.subject_objects(rdflib.OWL.equivalentProperty):
        s, o = str(s), str(o)
        if s.startswith(DBO) and "wikidata.org" in o:
            m[s[len(DBO):]].add(o.rsplit("/", 1)[-1])
    out = {k: {"props": sorted(v), "source": "ontology"} for k, v in m.items()}
    for k, (props, why) in MANUAL.items():
        if k not in out:
            out[k] = {"props": props, "source": "manual", "why": why}
    return out


def population():
    sv = json.load(open(os.path.join(HERE, "..", "results", "uniqueness_survey.json")))["results"]
    rows = [json.loads(l) for l in open(os.path.join(ROOT, "phase1_full", "triples.jsonl"))]
    freq = collections.Counter(r["rel"] for r in rows if r["status"] in ("verified", "faithful-unverified"))
    present = {p for p, r in sv.items() if r["fwd"].get("anchors", 0) > 0}
    return sv, rows, freq, present


# ── PART A ──────────────────────────────────────────────────────────────────
def histogram(props, direction):
    if direction == "fwd":
        q = (f"SELECT ?n (COUNT(?s) AS ?c) WHERE {{ {{ SELECT ?s (COUNT(DISTINCT ?o) AS ?n) WHERE {{ "
             f"?s {path(props)} ?o . {qid_ok('?o')} {POP} }} GROUP BY ?s }} }} GROUP BY ?n")
    else:
        q = (f"SELECT ?n (COUNT(?o) AS ?c) WHERE {{ {{ SELECT ?o (COUNT(DISTINCT ?s) AS ?n) WHERE {{ "
             f"?s {path(props)} ?o . {qid_ok('?o')} {POP} "
             f"?__b schema:about ?o ; schema:isPartOf <{ENWIKI}> . }} GROUP BY ?o }} }} GROUP BY ?n")
    rows = wq(q)
    if rows is None:
        return None
    return {int(b["n"]["value"]): int(b["c"]["value"]) for b in rows}


def summarise_hist(h):
    if not h:
        return {"anchors": 0}
    N = sum(h.values())
    return {"anchors": N,
            "pct_exactly_1": round(100 * h.get(1, 0) / N, 1),
            "pct_2_to_5": round(100 * sum(c for n, c in h.items() if 2 <= n <= 5) / N, 1),
            "pct_over_5": round(100 * sum(c for n, c in h.items() if n > 5) / N, 1),
            "max": max(h)}


def somevalue_anchors(props):
    rows = wq(f"SELECT (COUNT(DISTINCT ?s) AS ?c) WHERE {{ ?s {path(props)} ?o . "
              f"FILTER(STRSTARTS(STR(?o), \"{GENID}\")) {POP} }}")
    return None if rows is None else int(rows[0]["c"]["value"])


def containment_onehop(props, n_multi_total):
    """Share of multi-valued anchors that collapse to one value after removing
    values that contain another (one hop), from a uniform seeded sample."""
    pool = wq(f"SELECT ?s WHERE {{ {{ SELECT ?s (COUNT(DISTINCT ?o) AS ?n) WHERE {{ "
              f"?s {path(props)} ?o . {qid_ok('?o')} {POP} }} GROUP BY ?s }} FILTER(?n > 1) }} "
              f"LIMIT {args.multi_cap}", tsv=True)
    if not pool:
        return None, 0, False
    smp = random.Random(args.seed).sample(pool, min(args.multi_sample, len(pool)))
    vals = wq("SELECT ?s ?o WHERE { VALUES ?s { " + " ".join(f"<{s}>" for s in smp)
              + f" }} ?s {path(props)} ?o . {qid_ok('?o')} }}")
    if vals is None:
        return None, 0, False
    by = collections.defaultdict(set)
    for b in vals:
        by[b["s"]["value"]].add(b["o"]["value"])
    allv = sorted(set().union(*by.values())) if by else []
    edges = set()
    for i in range(0, len(allv), 300):
        rows = wq("SELECT ?u ?v WHERE { VALUES ?u { " + " ".join(f"<{v}>" for v in allv[i:i + 300])
                  + f" }} ?u {path(CONT_WD)} ?v . }}")
        if rows is None:
            return None, 0, False
        edges |= {(b["u"]["value"], b["v"]["value"]) for b in rows}
    collapsed = 0
    for s, vs in by.items():
        containers = {v for (u, v) in edges if u in vs and v in vs and u != v}
        if len(vs - containers) == 1:
            collapsed += 1
    return collapsed / len(by), len(by), len(pool) >= args.multi_cap


def part_a(mapping, sv, freq, present):
    rel_rows = {}
    pop_rels = [p for p, n in freq.most_common() if n >= args.min_freq and p in present and p in mapping]
    for k in KINSHIP:
        if k in mapping and k in present and k not in pop_rels:
            pop_rels.append(k)
    todo = [(r, mapping[r]["props"], mapping[r]["source"]) for r in pop_rels]
    todo += [(name, props, "wikidata-only") for name, props in EXTRA.items()]
    print(f"PART A: {len(todo)} relations\n", flush=True)
    t0 = time.time()
    for i, (rel, props, src) in enumerate(todo, 1):
        hf, hi = histogram(props, "fwd"), histogram(props, "inv")
        f, v = summarise_hist(hf), summarise_hist(hi)
        rec = {"relation": rel, "wikidata_props": props, "mapping": src,
               "phase1_freq": freq.get(rel, 0), "fwd": f, "inv": v,
               "query_failed": hf is None or hi is None}
        if hf:
            n_multi = sum(c for n, c in hf.items() if n > 1)
            frac, checked, capped = containment_onehop(props, n_multi) if n_multi else (0.0, 0, False)
            if frac is not None:
                rec["fwd"]["pct_unique_containment"] = round(
                    100 * (hf.get(1, 0) + frac * n_multi) / f["anchors"], 1)
                rec["fwd"]["containment_checked"] = checked
                rec["fwd"]["multi_pool_capped"] = capped
            else:
                rec["containment_failed"] = True
            sva = somevalue_anchors(props)
            if sva is not None:
                rec["pct_with_unknown_value"] = round(100 * sva / (f["anchors"] + sva), 2)
        dbp = sv.get(rel, {}).get("fwd", {})
        rec["dbpedia_fwd"] = {k: dbp.get(k) for k in ("anchors", "pct_exactly_1", "pct_unique_containment")}
        rel_rows[rel] = rec
        print(f"[{i:3d}/{len(todo)}] {rel:22s} {','.join(props):12s} "
              f"WD 1={f.get('pct_exactly_1', '-'):>5}% cont={rec['fwd'].get('pct_unique_containment', '-'):>5}%  "
              f"| DBp 1={dbp.get('pct_exactly_1', '-'):>5}% cont={dbp.get('pct_unique_containment', '-'):>5}%  "
              f"anchors WD={f.get('anchors', 0):>9,}  [{time.time() - t0:.0f}s]", flush=True)
    json.dump(rel_rows, open(os.path.join(args.out, "wd_population.json"), "w"), indent=1)
    return rel_rows


# ── PART B ──────────────────────────────────────────────────────────────────
WPAPI = "https://en.wikipedia.org/w/api.php"
_qid_cache = {}


def map_qids(names):
    """DBpedia local names -> Wikidata QIDs, through the English Wikipedia API.

    Not through Wikidata sitelinks directly: sitelinks exist only for current
    canonical titles, and DBpedia's 2022 snapshot is full of names that are now
    redirects (`Louis_XVI_of_France` vs `Louis_XVI`). The API resolves the
    redirect and returns the page's Wikidata item in one call, so every identity
    comparison in Part B is QID == QID on both KBs."""
    todo = sorted({n for n in names if n and n not in _qid_cache and "|" not in n and "#" not in n})
    for i in range(0, len(todo), 50):
        chunk = todo[i:i + 50]
        data = None
        for attempt in range(6):
            try:
                r = requests.get(WPAPI, params={"action": "query", "format": "json", "redirects": 1,
                                                "prop": "pageprops", "ppprop": "wikibase_item",
                                                "titles": "|".join(n.replace("_", " ") for n in chunk)},
                                 headers={"User-Agent": UA}, timeout=60)
                if r.status_code == 200:
                    data = r.json().get("query", {})
                    break
            except Exception:
                pass
            time.sleep(3 * (attempt + 1))
        for n in chunk:
            _qid_cache[n] = None
        if data is None:
            continue
        norm = {x["from"]: x["to"] for x in data.get("normalized", [])}
        redir = {x["from"]: x["to"] for x in data.get("redirects", [])}
        t2q = {p["title"]: p.get("pageprops", {}).get("wikibase_item")
               for p in data.get("pages", {}).values() if "missing" not in p}
        for n in chunk:
            t = n.replace("_", " ")
            t = norm.get(t, t)
            t = redir.get(t, t)
            _qid_cache[n] = t2q.get(t)
        time.sleep(0.3)
    return {n: _qid_cache[n] for n in names if _qid_cache.get(n)}


def values_dbpedia(rel, subjects):
    vals = collections.defaultdict(set)
    subjects = sorted(subjects)
    for i in range(0, len(subjects), 250):
        rows = dq("SELECT ?s ?v WHERE { VALUES ?s { " + " ".join(f"<{DBR}{s}>" for s in subjects[i:i + 250])
                  + f" }} ?s <{DBO}{rel}> ?v . FILTER(isIRI(?v)) }}")
        for b in rows or []:
            vals[b["s"]["value"][len(DBR):]].add(b["v"]["value"][len(DBR):] if b["v"]["value"].startswith(DBR)
                                                 else b["v"]["value"])
    return vals


def values_wikidata(props, qids):
    vals, unknown = collections.defaultdict(set), set()
    qids = sorted(qids)
    for i in range(0, len(qids), 200):
        rows = wq("SELECT ?s ?o WHERE { VALUES ?s { " + " ".join(f"<{WD}{q}>" for q in qids[i:i + 200])
                  + f" }} ?s {path(props)} ?o . }}")
        for b in rows or []:
            s, o = b["s"]["value"][len(WD):], b["o"]["value"]
            if o.startswith(WD + "Q"):
                vals[s].add(o[len(WD):])
            elif o.startswith(GENID):
                unknown.add(s)
    return vals, unknown


def containment_edges(kb, values):
    """Transitive containment edges among a set of values, same rule for both KBs."""
    vals = sorted(values)
    edges = set()
    for i in range(0, len(vals), 200):
        chunk, allv = vals[i:i + 200], vals
        if kb == "wd":
            rows = wq("SELECT ?u ?v WHERE { VALUES ?u { " + " ".join(f"<{WD}{v}>" for v in chunk)
                      + " } VALUES ?v { " + " ".join(f"<{WD}{v}>" for v in allv)
                      + f" }} ?u ({path(CONT_WD)})+ ?v . }}")
            pre = WD
        else:
            p = "|".join(f"<{DBO}{c}>" for c in CONT_DBO)
            rows = dq("SELECT ?u ?v WHERE { VALUES ?u { " + " ".join(f"<{DBR}{v}>" for v in chunk)
                      + " } VALUES ?v { " + " ".join(f"<{DBR}{v}>" for v in allv)
                      + f" }} ?u ({p})+ ?v . }}")
            pre = DBR
        for b in rows or []:
            u, v = b["u"]["value"], b["v"]["value"]
            if u.startswith(pre) and v.startswith(pre):
                edges.add((u[len(pre):], v[len(pre):]))
    return edges


def outcome(vs, edges):
    if not vs:
        return "none", None
    if len(vs) == 1:
        return "unique", next(iter(vs))
    leaves = vs - {v for (u, v) in edges if u in vs and v in vs and u != v}
    if len(leaves) == 1:
        return "unique_containment", next(iter(leaves))
    return "ambiguous", None


def family(rel):
    return "kinship" if rel in KINSHIP else "place" if rel in PLACE else "other"


def part_b(mapping, rows, present):
    facts = [r for r in rows if r["status"] in ("verified", "faithful-unverified")
             and r["rel"] in mapping and r["rel"] in present]
    print(f"\nPART B: {len(facts)} relational facts with a Wikidata mapping\n", flush=True)
    names = {r["sub"] for r in facts} | {r["obj"] for r in facts}
    q = map_qids(names)
    print(f"   mapped {len(q)}/{len(names)} entity names to QIDs "
          f"({100 * len(q) / max(len(names), 1):.1f}%)", flush=True)
    matched = [r for r in facts if r["sub"] in q]
    print(f"   facts whose subject has a QID: {len(matched)}/{len(facts)}", flush=True)

    by_rel = collections.defaultdict(list)
    for r in matched:
        by_rel[r["rel"]].append(r)
    dvals, wvals, wunknown = {}, {}, set()
    for rel, rs in by_rel.items():
        subs = {r["sub"] for r in rs}
        for s, v in values_dbpedia(rel, subs).items():
            dvals[(rel, s)] = v
        wv, unk = values_wikidata(mapping[rel]["props"], {q[s] for s in subs})
        for s in subs:
            wvals[(rel, s)] = wv.get(q[s], set())
            if q[s] in unk:
                wunknown.add((rel, s))
    multi_d = set().union(*[v for v in dvals.values() if len(v) > 1]) if dvals else set()
    multi_w = set().union(*[v for v in wvals.values() if len(v) > 1]) if wvals else set()
    print(f"   containment checks: {len(multi_d)} DBpedia values, {len(multi_w)} Wikidata values", flush=True)
    ed = containment_edges("dbp", multi_d) if multi_d else set()
    ew = containment_edges("wd", multi_w) if multi_w else set()

    res = []
    for r in matched:
        key = (r["rel"], r["sub"])
        dv, wv = dvals.get(key, set()), wvals.get(key, set())
        res.append((r, key, dv, wv, outcome(dv, ed), outcome(wv, ew)))
    # identity is compared as QID == QID on both sides (redirect-proof)
    q.update(map_qids({d[1] for (_, _, _, _, d, _) in res if d[1]}))

    out = []
    for r, key, dv, wv, (do, da), (wo, wa) in res:
        oq, daq = q.get(r["obj"]), (q.get(da) if da else None)
        out.append({"rel": r["rel"], "family": family(r["rel"]), "mapping": mapping[r["rel"]]["source"],
                    "sub": r["sub"], "obj": r["obj"], "sub_qid": q[r["sub"]], "obj_qid": oq,
                    "dbp_n": len(dv), "dbp_outcome": do, "dbp_answer": da, "dbp_answer_qid": daq,
                    "dbp_correct": (daq == oq) if (daq and oq) else None,
                    "wd_n": len(wv), "wd_outcome": wo, "wd_answer": wa,
                    "wd_correct": (wa == oq) if (wa and oq) else None,
                    "wd_unknown_value": key in wunknown})
    with open(os.path.join(args.out, "paired_facts.jsonl"), "w") as fh:
        for o in out:
            fh.write(json.dumps(o, ensure_ascii=False) + "\n")
    return out, len(facts), len(q), len(names)


def report_b(out, n_facts, n_mapped, n_names):
    def rates(rs, kb):
        n = len(rs)
        if not n:
            return {}
        cov = sum(1 for r in rs if r[f"{kb}_n"] > 0)
        uni = sum(1 for r in rs if r[f"{kb}_outcome"] == "unique")
        unc = sum(1 for r in rs if r[f"{kb}_outcome"] in ("unique", "unique_containment"))
        judged = [r for r in rs if r[f"{kb}_correct"] is not None]
        corr = sum(1 for r in judged if r[f"{kb}_correct"])
        return {"n": n, "coverage_pct": round(100 * cov / n, 1),
                "grounded_strict_pct": round(100 * uni / n, 1),
                "grounded_containment_pct": round(100 * unc / n, 1),
                "grounded_answer_matches_text_pct": round(100 * corr / len(judged), 1) if judged else None,
                "judged": len(judged)}
    summary = {"facts_with_mapping": n_facts, "entity_names": n_names, "entities_mapped_to_qid": n_mapped,
               "facts_matched": len(out),
               "all": {"dbpedia": rates(out, "dbp"), "wikidata": rates(out, "wd")},
               "by_family": {}, "by_mapping_source": {}, "paired": {}}
    for fam in ("kinship", "place", "other"):
        rs = [r for r in out if r["family"] == fam]
        summary["by_family"][fam] = {"dbpedia": rates(rs, "dbp"), "wikidata": rates(rs, "wd")}
    for src in ("ontology", "manual"):
        rs = [r for r in out if r["mapping"] == src]
        summary["by_mapping_source"][src] = {"dbpedia": rates(rs, "dbp"), "wikidata": rates(rs, "wd")}
    g = lambda r, kb: r[f"{kb}_outcome"] in ("unique", "unique_containment")
    summary["paired"] = {
        "both_ground": sum(1 for r in out if g(r, "dbp") and g(r, "wd")),
        "only_dbpedia": sum(1 for r in out if g(r, "dbp") and not g(r, "wd")),
        "only_wikidata": sum(1 for r in out if g(r, "wd") and not g(r, "dbp")),
        "neither": sum(1 for r in out if not g(r, "dbp") and not g(r, "wd")),
        "wd_unknown_value_facts": sum(1 for r in out if r["wd_unknown_value"]),
    }
    rel_tab = collections.defaultdict(list)
    for r in out:
        rel_tab[r["rel"]].append(r)
    summary["by_relation"] = {rel: {"dbpedia": rates(rs, "dbp"), "wikidata": rates(rs, "wd")}
                              for rel, rs in sorted(rel_tab.items(), key=lambda kv: -len(kv[1]))}
    json.dump(summary, open(os.path.join(args.out, "paired_summary.json"), "w"), indent=1)
    a = summary["all"]
    print("\n=== PAIRED, same facts, both KBs ===")
    for kb in ("dbpedia", "wikidata"):
        x = a[kb]
        print(f"  {kb:9s} n={x['n']}  coverage {x['coverage_pct']}%  grounded strict {x['grounded_strict_pct']}%  "
              f"containment {x['grounded_containment_pct']}%  answer==text {x['grounded_answer_matches_text_pct']}% "
              f"(of {x['judged']})")
    print("  paired:", summary["paired"])
    return summary


def main():
    os.makedirs(args.out, exist_ok=True)
    if wq("SELECT (COUNT(*) AS ?c) WHERE { ?s <http://www.wikidata.org/prop/direct/P26> ?o }") is None:
        sys.exit("QLever unreachable")
    ok = dq("SELECT ?s WHERE { ?s ?p ?o } LIMIT 1")
    if not ok:
        sys.exit("local DBpedia store unreachable on :7878")
    mapping = load_mapping()
    json.dump(mapping, open(os.path.join(args.out, "mapping_used.json"), "w"), indent=1)
    sv, rows, freq, present = population()
    t0 = time.time()
    if "A" in args.part:
        part_a(mapping, sv, freq, present)
    if "B" in args.part:
        out, n_facts, n_mapped, n_names = part_b(mapping, rows, present)
        report_b(out, n_facts, n_mapped, n_names)
    print(f"\ndone in {time.time() - t0:.0f}s -> {args.out}")


if __name__ == "__main__":
    main()
