"""API 라우트 — /ingest, /query. [delegate 배선]

인제스트:  text → chunk_text → embed → insert_chunks (pgvector)
질의:      question → search(top-k) → generate (Ollama, 출처 포함)
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.db.pgvector import insert_chunks
from app.rag.chunking import chunk_text
from app.rag.embedding import embed
from app.rag.generation import generate
from app.rag.retrieval import search

router = APIRouter()


class IngestRequest(BaseModel):
    text: str
    source: str


class IngestResponse(BaseModel):
    inserted: int


class QueryRequest(BaseModel):
    question: str
    k: int = 5


@router.post("/ingest", response_model=IngestResponse)
def ingest(req: IngestRequest) -> IngestResponse:
    chunks = chunk_text(req.text)
    embeddings = embed(chunks)
    n = insert_chunks(chunks, embeddings, {"source": req.source})
    return IngestResponse(inserted=n)


@router.post("/query")
def query(req: QueryRequest) -> dict:
    contexts = search(req.question, k=req.k)
    return generate(req.question, contexts)
