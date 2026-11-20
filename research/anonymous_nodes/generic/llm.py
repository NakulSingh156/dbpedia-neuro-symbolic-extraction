"""One JSON-returning LLM call for local Ollama models and OpenRouter models, with cost accounting.

model names: "llama3.1:8b", "qwen2.5:7b" (Ollama) | "openrouter:openai/gpt-5.6-luna" (OpenRouter; key in OPENROUTER_API_KEY).
Every call appends {model, latency_s, prompt_tokens, completion_tokens, cost_usd} to CALLS.
"""
import json, os, time, requests

CALLS = []
OLLAMA = "http://localhost:11434/api/generate"
OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"


def llm_json(prompt, model, temperature=0, max_tokens=800, timeout=300):
    t0 = time.time()
    meta = {"model": model, "latency_s": None, "prompt_tokens": None, "completion_tokens": None, "cost_usd": 0.0, "error": None}
    text = ""
    try:
        if model.startswith("openrouter:"):
            r = requests.post(OPENROUTER, timeout=timeout, headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
                              json={"model": model.split(":", 1)[1], "messages": [{"role": "user", "content": prompt}],
                                    "temperature": temperature, "max_tokens": max_tokens,
                                    "response_format": {"type": "json_object"}, "usage": {"include": True}})
            j = r.json()
            if "choices" not in j:
                raise RuntimeError(str(j)[:200])
            text = j["choices"][0]["message"]["content"] or ""
            u = j.get("usage", {})
            meta.update(prompt_tokens=u.get("prompt_tokens"), completion_tokens=u.get("completion_tokens"), cost_usd=u.get("cost") or 0.0)
        else:
            r = requests.post(OLLAMA, timeout=timeout, json={"model": model, "prompt": prompt, "format": "json", "stream": False,
                                                            "options": {"temperature": temperature, "num_predict": max_tokens}})
            j = r.json(); text = j.get("response", "")
            meta.update(prompt_tokens=j.get("prompt_eval_count"), completion_tokens=j.get("eval_count"))
    except Exception as e:
        meta["error"] = f"{type(e).__name__}: {str(e)[:150]}"
    meta["latency_s"] = round(time.time() - t0, 2)
    CALLS.append(meta)
    try:
        return json.loads(text), meta
    except Exception:
        s, e = text.find("{"), text.rfind("}")
        try:
            return json.loads(text[s:e + 1]), meta
        except Exception:
            return None, meta
