"""
Module 8 Project — Containerized RAG Assistant  (STARTER)
Backend: FastAPI Application
=============================
Run locally:
    uvicorn main:app --reload --port 8000

Your task: implement the four endpoint handlers below.
The RAG logic lives in rag.py — import and call those functions here.

Required endpoints:
    GET  /          → welcome message
    POST /ask       → RAG query: retrieve + generate + return answer + sources
    POST /ingest    → load documents from ./docs and store in ChromaDB
    GET  /stats     → document count, model name, db path
    GET  /health    → ChromaDB status, Ollama connectivity, document count
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
import requests
from config import settings
import rag

app = FastAPI(title="RAG API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOCS_DIR = "./docs"

# ── Request / Response schemas ─────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str
    n_results: int = 3
    max_distance: float = 1.2

    @field_validator("question")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question must not be empty")
        return v


class SourceChunk(BaseModel):
    text: str
    source: str
    distance: float


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    confidence: str


class IngestResponse(BaseModel):
    chunks_ingested: int
    message: str


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/")
def root():
    #: Return a welcome dict, e.g. {"message": "RAG API is running", "docs": "/docs"}
    return {"message": "RAG API is running", 
            "docs": "/docs"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    """
    RAG query pipeline:
      1. rag.retrieve(req.question, req.n_results, req.max_distance)
      2. If no chunks, return a helpful "no documents" response
      3. rag.build_prompt(req.question, chunks)
      4. rag.generate(messages)
      5. rag.compute_confidence(chunks)
      6. Return AskResponse

    : Implement this endpoint.
    """
    chunks = rag.retrieve(
        req.question,
        req.n_results,
        req.max_distance
    )
    if not chunks:
        return AskResponse(
            answer=("No relevant documents found."),
            sources=[],
            confidence="low",
        )
    messages = rag.build_prompt(
        req.question,
        chunks
    )

    answer = rag.generate(messages)

    confidence = rag.compute_confidence(chunks)

    sources = [
        SourceChunk(
            text=chunk["text"],
            source=chunk["metadata"]["source"],
            distance=chunk["distance"],
        )
        for chunk in chunks
    ]

    return AskResponse(
        answer=answer,
        sources=sources,
        confidence=confidence,
    )


@app.post("/ingest", response_model=IngestResponse)
def ingest():
    """
    Load documents from DOCS_DIR and upsert into ChromaDB.
      1. rag.load_documents(DOCS_DIR)
      2. If empty, return a helpful message
      3. rag.collection.upsert(documents=..., metadatas=..., ids=...)
      4. Return IngestResponse with count

    : Implement this endpoint.
    Hint: access the ChromaDB collection via rag.collection
    """
    #: implement
    docs = rag.load_documents(DOCS_DIR)
    if not docs:
        return IngestResponse(               
            chunks_ingested=0, 
            message="No documents to ingest.")
    
    rag.collection.upsert(
        documents=[d["text"] for d in docs],
        metadatas=[d["metadata"] for d in docs],
        ids=[d["id"] for d in docs],
    )
    return IngestResponse(
        chunks_ingested=len(docs), 
        message=f"Successfully ingested {len(docs)} documents.")


@app.get("/stats")
def stats():
    """
    Return document count, model name, and db path.
    : Return a dict with "document_count", "model", and "db_path".
    Hint: rag.collection.count(), settings.model_name, settings.chroma_path
    """
    #: implement
    return {
        "document_count": rag.collection.count(),
        "model": settings.model_name,
        "db_path": settings.chroma_path,
    }

@app.get("/health")
def health():
    """
    Return status of ChromaDB and Ollama.
    : Implement this endpoint.

    Suggested response shape:
        {
            "status":         "ok" | "degraded",
            "chromadb":       "ok" | "error",
            "ollama":         "connected" | "disconnected",
            "document_count": <int>,
        }

    To check Ollama: try GET settings.ollama_url + "/api/tags" with a short timeout.
    """
    #: implement
    #ChromaDB status
    try:
        document_count = rag.collection.count()
        chromadb_status = "ok"
    except Exception:
        document_count = 0
        chromadb_status = "error"

    # Check Ollama
    try:
        response = requests.get(
            f"{settings.ollama_url}/api/tags",
            timeout=5,
        )

        response.raise_for_status()
        ollama_status = "connected"

    except requests.RequestException:
        ollama_status = "disconnected"

    if chromadb_status == "ok" and ollama_status == "connected":
        overall_status = "ok"
    else:
        overall_status = "degraded"

    return {
        "status": overall_status,
        "chromadb": chromadb_status,
        "ollama": ollama_status,
        "document_count": document_count
    }
