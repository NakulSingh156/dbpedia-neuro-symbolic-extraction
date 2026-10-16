"""M1 — detect unnamed non-topic entities and parse them into the Description IR (METHODOLOGY.md §3.3).

One LLM call per sentence (local Ollama by default), JSON out, then the lexicon maps relation nouns
to KB paths (M3, lexicon step). Few-shot examples are synthetic (not taken from any dev/test item).
"""
import json, re, requests
from .ir import Description, Anchor, Constraints
from .lexicon import expand, entry

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


POSSESSIVE = ("his ", "her ", "its ", "their ")
PREPOSITIONS = {"in", "at", "on", "from", "to", "for", "with", "of", "by", "during", "after", "before", "into", "near"}
# a name right after the mention means the entity IS named in the sentence:
# "his brother Kelle", "His father, Young Hur", "Her aunt was the actress Maxine Elliott", "Son - Sin Chong"
NAMED_AFTER = re.compile(
    r"^(?:\s*[,:\-–]?\s*[A-Z]"                                                   # "his brother Kelle", "Son - Sin"
    r"|\s*,?\s*(?:was|is|were)\s+the\s+(?:[a-z][\w\-]*\s+){0,2}[A-Z]"   # "was the actress Maxine" (not "was a National Liberal ...")
    r"|\s*,\s*the\s+(?:[a-z][\w\-]*\s+){0,2}[A-Z])")                     # ", the actor John"
# a role OF a named organisation describes someone named elsewhere or the topic itself, not an unnamed entity:
# "director of the influential Gazette des Beaux-Arts", "a member of the Audit Commission"
ROLE_OF_NAMED = re.compile(r"^(?:the |a |an )?(?:[\w\-]+ ){0,2}(?:director|author|founder|co-founder|chairman|member|members|president|manager|leader)s? of (?:the )?(?:[\w\-]+ ){0,2}[A-Z]")


def keep(d, sentence, version=3):
    """Post-filter on M1 output. Version history (all measured):
    v1 (16 Oct): path must map via the lexicon.
    v2 (16 Oct): + mention occurs in the sentence (or, 17 Oct, its relation noun does); + reads as a description;
                 + not after a copula. Dev: 59/60 -> 1/60 false alarms. Natural-dev (17 Oct): only 51 of 172 kept
                 sentences genuine.
    v3 (17 Oct): + empty chains rejected; + rejected when a name follows the mention (named in the sentence),
                 checked at the relation word when the LLM normalised the mention; + roles of a named organisation
                 rejected; + a lexicon relation word must occur in the mention, or the mention must be possessive.
                 Tuned on NATURAL-DEV (45 biographies) — held-out numbers need new biographies."""
    if not d.paths or not d.relation_phrases:
        return False
    m = d.mention.lower().strip()
    sl = sentence.lower()
    last = d.relation_phrases[-1]
    if not m or (m not in sl and not (last and last in sl)):
        return False
    pos, end = sl.find(m), None
    if pos >= 0:
        end = pos + len(m)
        before = sl[:pos].rstrip()
        if before.endswith((" was", " is", " were", " are", " as", " became", " becomes")):
            return False
    elif version >= 3:
        # normalised mention ("his sister" for "Rhoads' sister Kathy"): check right after the relation word instead
        k = sl.find(last)
        end = k + len(last) if k >= 0 else None
        while end is not None and end < len(sl) and sl[end].isalpha():      # "sister" -> "sisters"
            end += 1
    if version >= 3:
        if end is not None and NAMED_AFTER.match(sentence[end:]):
            return False
        if ROLE_OF_NAMED.match(d.mention.strip()):
            return False
    if version >= 3:
        def word(w):
            w = re.sub(r"(['’]s|['’])$", "", w.strip(".,;:()\"“”"))      # "mother's" -> mother, "brothers'" -> brothers
            return entry(w) or (w.endswith("s") and entry(w[:-1]))
        has_rel_word = any(word(w) for w in m.split())
        # inverse pattern: "the second son of a daimyo of the Akizuki clan" — the description holds no relation word
        inverse = pos > 0 and re.search(r"\b(?:son|daughter|child|sons|daughters|children|wife|husband|widow) of$", sl[:pos].rstrip())
        possessive = m.startswith(POSSESSIVE) or "'s " in m or "’s " in m or "s' " in m
        return bool(has_rel_word or possessive or inverse)
    return (last and last in m) or m.startswith(("a ", "an ", "the ", "his ", "her ", "its ", "their ", "another ", "one of ")) or "'s " in m


def pronoun_anchor_ambiguous(d, sentence):
    """M2 safety (17 Oct): a possessive pronoun ("his father") after an earlier relational description in the same
    sentence ("Alexander Grin's son ... his father's life") may point to that description, not to the topic.
    Grounding it on the topic gave the only 2 wrong identities in the paraphrased controlled set -> abstain instead."""
    m = d.mention.lower().strip()
    if d.anchor.ref != "topic" or not m.startswith(POSSESSIVE):
        return False
    sl = sentence.lower()
    k = sl.find(m) if m in sl else sl.find(d.relation_phrases[-1]) if d.relation_phrases else -1
    before = sl[:k] if k > 0 else ""
    for mm in re.finditer(r"(?:[\w\-]+['’]s?|\b(?:his|her|its|their)|\bthe [\w\-]+ of)\s+([\w\-]+)", before):
        if entry(mm.group(1)) or entry(mm.group(1).rstrip("s")):
            return True
    return False


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
