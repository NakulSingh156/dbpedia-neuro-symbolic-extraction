"""M1 — detect unnamed non-topic entities and parse them into the Description IR (METHODOLOGY.md §3.3).

One LLM call per sentence (local Ollama by default), JSON out, then the lexicon maps relation nouns
to KB paths (M3, lexicon step). Few-shot examples are synthetic (not taken from any dev/test item).
"""
import json, requests
from .ir import Description, Anchor, Constraints
from .lexicon import expand

PROMPT = """You find entities that a sentence refers to WITHOUT naming them, through their relation to another entity
("his brother", "Marie Antoinette's husband", "the founder of Rome", "the grandson of the founder of Rome").

Text about {topic}:
{context}

Sentence: "{sentence}"

List every such description in the sentence. Do NOT list: pronouns for {topic} itself ("he", "she", "it"),
descriptions of {topic} itself ("the film", "the village"), generic phrases ("people", "many fans"),
or entities named in the sentence.

For each one give:
- "mention": the exact words in the sentence
- "anchor": the entity it is described relative to ({topic} if it is "his/her/its ..."), as a name
- "relations": relation nouns from the anchor outward, singular, lower case, e.g. ["brother"], ["founder", "grandson"], ["father"] for "the son of a farmer" (the farmer is the father)
- "gender": "male", "female" or null
- "plural": true if it refers to several entities
- "named_in_text": the entity's name if the text names it somewhere else, otherwise null

Examples:
Sentence: "Her husband was a famous painter." (text about Anna Berg) -> {{"items": [{{"mention": "Her husband", "anchor": "Anna Berg", "relations": ["husband"], "gender": "male", "plural": false, "named_in_text": null}}]}}
Sentence: "The castle was sold to the grandson of the founder of Leeds." -> {{"items": [{{"mention": "the grandson of the founder of Leeds", "anchor": "Leeds", "relations": ["founder", "grandson"], "gender": "male", "plural": false, "named_in_text": null}}]}}
Sentence: "He was born in Lyon." -> {{"items": []}}

Reply as JSON: {{"items": [...]}}"""


DETERMINERS = ("a ", "an ", "the ", "his ", "her ", "its ", "their ", "another ", "one of ")


def keep(d, sentence):
    """Post-filter (dev, 16 Oct). Keep a detection only if
    (1) its relation chain maps to a KB path through the lexicon,
    (2) the mention really occurs in the sentence, and
    (3) the mention contains its relation noun or reads as a description (starts with a determiner/possessive),
        not as a bare name ("Giovanni Battista Draghi"), and
    (4) it does not follow a copula (see below).
    Without the filter, 23/60 dev negative sentences got a detection; with (1) alone, 5/60."""
    if not d.paths:
        return False
    m = d.mention.lower().strip()
    if not m or m not in sentence.lower():
        return False
    # (4) a description right after a copula describes the sentence's own subject ("X was the capital of Y",
    #     "served as a member of Z"), not another entity
    before = sentence.lower().split(m, 1)[0].rstrip()
    if before.endswith((" was", " is", " were", " are", " as", " became", " becomes")):
        return False
    last = d.relation_phrases[-1] if d.relation_phrases else ""
    return (last and last in m) or m.startswith(DETERMINERS) or "'s " in m


def detect(sentence, topic, context, model="qwen2.5:7b", url="http://localhost:11434/api/generate"):
    try:   # num_predict caps runaway JSON (llama3.1 can emit whitespace forever in JSON mode)
        r = requests.post(url, timeout=300, json={"model": model, "format": "json", "stream": False,
                                                  "options": {"temperature": 0, "num_predict": 800},
                                                  "prompt": PROMPT.format(topic=topic, context=context, sentence=sentence)})
    except requests.RequestException as e:
        return [], f"llm-error: {type(e).__name__}"
    try:
        items = json.loads(r.json()["response"]).get("items", [])
    except Exception:
        return [], r.json().get("response", "")[:300]
    out = []
    for it in items if isinstance(items, list) else []:
        try:
            rel = [str(x).lower().strip() for x in it.get("relations") or []]
            anchor_text = str(it.get("anchor") or topic)
            d = Description(mention=str(it.get("mention", "")), role="unknown",
                            anchor=Anchor("topic" if anchor_text.strip().lower() == topic.lower() else "mention", anchor_text),
                            relation_phrases=rel,
                            constraints=Constraints(gender=it.get("gender") if it.get("gender") in ("male", "female") else None,
                                                    plural=bool(it.get("plural"))),
                            evidence={"named_in_text": it.get("named_in_text")})
            for kb in ("wikidata", "dbpedia"):
                alts, g = expand(rel, kb)
                if alts:
                    d.paths[kb] = alts
                    if d.constraints.gender is None and g:
                        d.constraints.gender = g
            out.append(d)
        except Exception:
            continue
    return out, None
