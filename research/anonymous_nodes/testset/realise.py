"""Surface realisation for controlled items (METHODOLOGY.md §6.1, 'templates -> LLM paraphrase').

Each item becomes a 2-sentence text: a TRUE intro built from the anchor's Wikidata description, then a
sentence that uses the description with a neutral predicate that asserts nothing a KB could check
("... is mentioned in several accounts of his life"). Three forms: possessive, of-phrase, pronoun.
Optional --paraphrase: a local LLM rewrites the second sentence; kept only if the description words
survive verbatim, else the template stays (and the attempt is counted).
-> testset/prototype/realised.jsonl
"""
import json, os, random, re, sys, requests
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from generic.kb_wikidata import WikidataKB   # noqa: E402

FORMS = ("possessive", "of_phrase", "pronoun")
EVENTS = ["is mentioned in several accounts of {obj} life.", "also appears in a biography of {obj2}."]
kb = WikidataKB()

def descriptions(qids):
    out = {}
    for i in range(0, len(qids), 50):
        j = kb.api("https://www.wikidata.org/w/api.php", {"action": "wbgetentities", "ids": "|".join(qids[i:i + 50]),
                                                          "props": "descriptions", "languages": "en"})
        for q, e in j.get("entities", {}).items():
            out[q] = e.get("descriptions", {}).get("en", {}).get("value")
    return out

def realise(it, desc, form, rnd):
    male = it.get("anchor_gender", "male") == "male"
    subj, obj, obj2 = ("He", "his", "him") if male else ("She", "her", "her")
    name = re.sub(r"\s*\([^)]*\)$", "", it["anchor"])      # "Patrick Stirling (footballer)" -> "Patrick Stirling"
    intro = f"{name} is {('an ' if desc[:1].lower() in 'aeiou' else 'a ') + desc}." if desc else f"{name} is the subject of this text."
    ev = rnd.choice(EVENTS).format(obj=obj, obj2=obj2)
    mention = {"possessive": f"{name}'s {it['noun']}", "of_phrase": f"The {it['noun']} of {name}",
               "pronoun": f"{obj.capitalize()} {it['noun']}"}[form]
    return intro, f"{mention} {ev}", mention

def paraphrase(sentence, mention, model="qwen2.5:7b"):
    prompt = (f'Rewrite this sentence so it sounds natural in an encyclopedia, keeping the exact words "{mention}" unchanged '
              f'and adding no new facts:\n"{sentence}"\nReply as JSON: {{"sentence": "..."}}')
    try:
        r = requests.post("http://localhost:11434/api/generate", timeout=120, json={"model": model, "prompt": prompt,
                          "format": "json", "stream": False, "options": {"temperature": 0.7, "num_predict": 200}})
        s = json.loads(r.json()["response"]).get("sentence", "")
    except Exception:
        return None
    return s if mention in s else None

if __name__ == "__main__":
    para = "--paraphrase" in sys.argv
    items = [json.loads(l) for l in open(os.path.join(HERE, "prototype/cells.jsonl"))]
    d = descriptions(sorted({it["anchor_qid"] for it in items}))
    rnd = random.Random(3)
    out, kept, tried = [], 0, 0
    for k, it in enumerate(items):
        form = FORMS[k % 3]
        intro, sent, mention = realise(it, d.get(it["anchor_qid"]), form, rnd)
        if para:
            tried += 1
            p = paraphrase(sent, mention)
            if p: sent, kept = p, kept + 1
        out.append({**it, "form": form, "text": f"{intro} {sent}", "intro": intro, "sentence": sent, "mention": mention})
    with open(os.path.join(HERE, "prototype/realised.jsonl"), "w") as f:
        for o in out: f.write(json.dumps(o, ensure_ascii=False) + "\n")
    print(f"realised {len(out)} items; paraphrase kept {kept}/{tried}")
    for o in out[:6]: print(" ", o["form"], "|", o["text"])
