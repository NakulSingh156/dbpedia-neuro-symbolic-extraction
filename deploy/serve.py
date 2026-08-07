"""Minimal extraction endpoint — DRAFT.

Wraps the frozen pipeline's extract_all_triples() behind one HTTP call:

    POST /extract   {"text": "The song Mermaid is by the band Train."}
    → {"triples": [{"sub": ..., "rel": ..., "obj": ..., "status": ...}, ...]}

Every triple carries its verification status (verified / faithful-unverified),
so downstream users can filter by trust level.
"""
import os

from fastapi import FastAPI
from pydantic import BaseModel

os.environ.setdefault("USE_TF", "0")
import autonomous_pipeline_v13 as pl

app = FastAPI(title="DBpedia NEF-style extraction service")


class ExtractRequest(BaseModel):
    text: str


@app.get("/health")
def health():
    return {"ok": True, "model": pl.TARGET_MODEL}


@app.post("/extract")
def extract(req: ExtractRequest):
    results = pl.extract_all_triples(req.text)
    return {"triples": results}
