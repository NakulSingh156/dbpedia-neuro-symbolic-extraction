"""Density probe: are relational descriptions denser in full biography articles than in abstracts?

Same people on both sides: persons (dbo:Person in the local store) among the 2,000 Phase-1
abstract topics, seed 11. Full article text from the Wikipedia API (plain extract, wiki section
markers); lead section (before the first heading) vs body. List-like sections (references,
works, filmography, ...) are dropped. Both sides split with the canonical splitter and run
through scan.py. Hits are verified by hand in density_verified.py.
-> results/density_sentences.jsonl, results/density_hits.jsonl
"""
import json, os, random, re, sys, time, requests
from urllib.parse import unquote
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "../../../scripts"))
from sentence_split import split_sentences  # noqa: E402
from scan import scan  # noqa: E402

N, SEED = 50, 11
STORE = "http://localhost:7878/query"
UA = {"User-Agent": "nef-research/0.1 (https://github.com/NakulSingh156/dbpedia-neuro-symbolic-extraction; research script)"}
SKIP = re.compile(r"^(references|notes|external links|see also|further reading|bibliography|works|"
                  r"filmography|discography|selected works|publications|sources|citations|honours|honors|"
                  r"awards|footnotes|gallery)", re.I)

A = [json.loads(l) for l in open(os.path.join(HERE, "all_sentences.jsonl"))]
topics = sorted({x["abstract_uri"] for x in A})
def is_person(u):
    r = requests.post(STORE, data={"query": f"ASK {{ <{u}> a <http://dbpedia.org/ontology/Person> }}"},
                      headers={"Accept": "application/sparql-results+json"}, timeout=30)
    return r.json()["boolean"]
persons = [u for u in topics if is_person(u)]
pick = sorted(random.Random(SEED).sample(persons, N))
print(f"topics {len(topics)} | persons {len(persons)} | sampled {len(pick)}", flush=True)

CACHE = os.path.join(HERE, "results/density_extracts_cache.json")
cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
rows = []
for u in pick:
    title = unquote(u.rsplit("/", 1)[1]).replace("_", " ")
    if title in cache:
        j = cache[title]
    else:
      for attempt in range(6):
        r = requests.get("https://en.wikipedia.org/w/api.php", headers=UA, timeout=60, params={
            "action": "query", "prop": "extracts", "explaintext": 1, "exsectionformat": "wiki",
            "redirects": 1, "titles": title, "format": "json"})
        if r.status_code == 200 and r.text.startswith("{"):
            j = r.json(); cache[title] = j; json.dump(cache, open(CACHE, "w")); time.sleep(3); break
        print("   retry", title, r.status_code, flush=True); time.sleep(20 * (attempt + 1))
      else:
        print("   skip", title, flush=True); continue
    page = next(iter(j["query"]["pages"].values()))
    text = page.get("extract") or ""
    parts = re.split(r"\n(={2,6})\s*(.+?)\s*\1\n", text)
    lead, body, skipping = parts[0], [], False
    for i in range(1, len(parts) - 2, 3):
        level, head, chunk = len(parts[i]), parts[i + 1], parts[i + 2]
        if level == 2: skipping = bool(SKIP.match(head))
        if not skipping: body.append(chunk)
    for src, txt in (("article_lead", lead), ("article_body", "\n".join(body))):
        for k, s in enumerate(split_sentences(re.sub(r"\s*\n+\s*", " ", txt))):
            rows.append({"topic": u, "source": src, "k": k, "sentence": s})
    for x in A:
        if x["abstract_uri"] == u:
            rows.append({"topic": u, "source": "dbpedia_abstract", "k": x["pos"], "sentence": x["sentence"], "id": x["id"]})

os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
with open(os.path.join(HERE, "results/density_sentences.jsonl"), "w") as f:
    for i, r in enumerate(rows):
        r["did"] = f"d{i:05d}"; f.write(json.dumps(r, ensure_ascii=False) + "\n")
n_hit = 0
with open(os.path.join(HERE, "results/density_hits.jsonl"), "w") as f:
    for r in rows:
        h = scan(r["sentence"])
        if h:
            n_hit += 1; f.write(json.dumps({**r, "hits": [x["span"] for x in h]}, ensure_ascii=False) + "\n")
from collections import Counter
c = Counter(r["source"] for r in rows)
print("sentences by source:", dict(c), "| hit sentences:", n_hit)
