
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from app.retrieval import KnowledgeRetriever
from app.rag import RAGService


app = FastAPI(
    title="AI Commerce Support Assistant",
    version="0.2.0",
    description="RAG-powered ecommerce customer support API",
)


class SupportQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


@lru_cache
def get_retriever() -> KnowledgeRetriever:
    return KnowledgeRetriever()


@lru_cache
def get_rag_service() -> RAGService:
    return RAGService(retriever=get_retriever())


@app.get("/")
def root():
    return {
        "project": "AI Commerce Support Assistant",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


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


@app.post("/support/ask")
def ask_support(request: SupportQuestion):
    return get_rag_service().answer(request.question)