"""B1 in plain extraction mode (pre-meeting teaser, NOT the real baseline): the 23 descriptions of
headroom_teaser.json, but the LLM is asked to extract KG triples with canonical entity names and is
never told it may say UNKNOWN. What happens to the unnamed entity: named correctly, named wrongly
(hallucinated identity), kept as a phrase ("Arthur Winter's brother"), or the fact dropped?
-> results/extraction_mode.json ; grading by hand in extraction_graded.py
"""
import json, os, requests
HERE = os.path.dirname(os.path.abspath(__file__))
H = json.load(open(os.path.join(HERE, "results/headroom_teaser.json")))
A = [json.loads(l) for l in open(os.path.join(HERE, "all_sentences.jsonl"))]
by_id = {x["id"]: x for x in A}
abstract = {}
for x in A: abstract.setdefault(x["abstract_uri"], []).append(x["sentence"])

PROMPT = """You are building a knowledge graph from Wikipedia text.

Context (Wikipedia abstract about {topic}):
{context}

Extract every factual triple stated in this sentence:
"{sentence}"

Rules: use canonical entity names as they would appear as Wikipedia article titles for subjects and objects
(resolve pronouns and descriptions to the entity they refer to). Use short relation names.
Reply as JSON: {{"triples": [["subject", "relation", "object"], ...]}}"""

out = []
for r in H:
    x = by_id[r["id"]]
    row = {"id": r["id"], "span": r["span"], "anchor": r["anchor"], "kb_outcome": r["kb_outcome"],
           "kb_answers": r["kb_answers"], "sentence": x["sentence"], "llm": {}}
    for m in ("qwen2.5:7b", "llama3.1:8b"):
        resp = requests.post("http://localhost:11434/api/generate", timeout=300, json={
            "model": m, "format": "json", "stream": False, "options": {"temperature": 0},
            "prompt": PROMPT.format(topic=x["topic"], context=" ".join(abstract[x["abstract_uri"]]), sentence=x["sentence"])})
        try: row["llm"][m] = json.loads(resp.json()["response"]).get("triples", [])
        except Exception: row["llm"][m] = resp.json().get("response", "")[:400]
    out.append(row)
    print(f'\n{r["id"]} [{r["span"]}] KB={r["kb_outcome"]} {[a[1] for a in r["kb_answers"]]}\n  {x["sentence"][:150]}')
    for m in row["llm"]: print(f"  {m[:6]}: {json.dumps(row['llm'][m], ensure_ascii=False)[:400]}")
json.dump(out, open(os.path.join(HERE, "results/extraction_mode.json"), "w"), indent=1, ensure_ascii=False)
