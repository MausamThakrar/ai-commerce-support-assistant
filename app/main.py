
from fastapi import FastAPI

app = FastAPI(
    title="AI Commerce Support Assistant",
    version="0.1.0",
    description="RAG-powered ecommerce customer support API",
)


@app.get("/")
def root():
    return {
        "project": "AI Commerce Support Assistant",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


from functools import lru_cache

from fastapi import HTTPException, Query
from app.retrieval import KnowledgeRetriever


@lru_cache
def get_retriever() -> KnowledgeRetriever:
    return KnowledgeRetriever()


@app.get("/support/search")
def search_knowledge(
    q: str = Query(min_length=1),
    top_k: int = Query(default=3, ge=1, le=10),
):
    try:
        results = get_retriever().search(q, top_k)
        return {"query": q, "results": results}
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc