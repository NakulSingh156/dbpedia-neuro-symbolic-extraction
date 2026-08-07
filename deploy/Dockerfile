# Pipeline service image — DRAFT (deployment packaging, post-v14-final).
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    rdflib redis pydantic requests numpy \
    langchain-core langchain-openai langgraph \
    sentence-transformers rank-bm25 \
    fastapi uvicorn

COPY autonomous_pipeline_v13.py surface_index.py chunked_runner.py \
     repair_tiers.py per_sentence_timeout.py dbpedia.owl ./
COPY deploy/serve.py ./

EXPOSE 8000
CMD ["uvicorn", "serve:app", "--host", "0.0.0.0", "--port", "8000"]
