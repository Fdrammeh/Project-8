"""
Module 8 Project — Containerized RAG Assistant  (STARTER)
Backend: RAG Pipeline
======================
This is the core of your RAG application.
Implement each function below, then wire them into main.py.

Pipeline overview:
    1. load_documents(directory)  — read .txt / .md files and split into chunks
    2. retrieve(query, n)         — query ChromaDB for the most relevant chunks
    3. build_prompt(question, chunks) — format system prompt + context
    4. generate(messages)         — call Ollama's /api/chat endpoint
    5. compute_confidence(chunks) — rate result quality from distances

Run locally to test before wiring to FastAPI:
    python rag.py
"""

import os
import requests
import chromadb
from config import settings

# ── ChromaDB client ────────────────────────────────────────────────────────
# Create a PersistentClient pointed at settings.chroma_path
chroma_client = chromadb.PersistentClient(path=settings.chroma_path)
collection = chroma_client.get_or_create_collection(name = "documents")


# ── 1. Document loading ────────────────────────────────────────────────────

def load_documents(directory: str) -> list[dict]:
    """
    Read all .txt and .md files in `directory`.
    Split each file into paragraphs (split on blank lines).
    Return a list of dicts with keys: "text", "id", "metadata".

    Each chunk dict should look like:
        {
            "text":     "the paragraph text",
            "id":       "filename_0",          # unique id per chunk
            "metadata": {"source": "filename", "chunk_index": "0"},
        }

     Implement this function.
    Steps:
      1. os.listdir(directory) — iterate over files ending in .txt or .md
      2. Read each file and split on "\\n\\n"
      3. Build a dict for each non-empty paragraph
      4. Return the list
    """
    chunks = []

    for filename in sorted(os.listdir(directory)):
        if not filename.endswith((".txt", ".md")):
            continue

        filepath = os.path.join(directory, filename)

        with open(filepath, "r", encoding="utf-8") as file:
            content = file.read()

        paragraphs = content.split("\n\n")

        for index, paragraph in enumerate(paragraphs):
            text = paragraph.strip()

            if not text:
                continue

            chunks.append(
                {
                    "text": text,
                    "id": f"{filename}_{index}",
                    "metadata": {
                        "source": filename,
                        "chunk_index": str(index),
                    },
                }
            )

    return chunks


# ── 2. Retrieval ───────────────────────────────────────────────────────────

def retrieve(query: str, n_results: int = 3, max_distance: float = 1.2) -> list[dict]:
    """
    Query ChromaDB for the `n_results` most relevant chunks.
    Filter out any chunks with distance > max_distance.
    Return a list of dicts with keys: "text", "metadata", "distance".

    : Implement this function.
    Steps:
      1. Check collection.count() — return [] if empty
      2. collection.query(query_texts=[query], n_results=...)
      3. Zip documents, metadatas, and distances into result dicts
      4. Filter by max_distance
    """
    if collection.count() == 0:
        return []

    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    chunks = []

    for text, metadata, distance in zip(
        documents,
        metadatas,
        distances
    ):
        if distance <= max_distance:
            chunks.append(
                {
                    "text": text,
                    "metadata": metadata,
                    "distance": distance,
                }
            )

    return chunks


# ── 3. Prompt building ─────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are a helpful AI assistant. Answer ONLY from the provided context. "
    "If the context doesn't contain the answer, say you don't have enough "
    "information. Cite source documents by name. Keep responses under 200 words."
)


def build_prompt(question: str, chunks: list[dict]) -> list[dict]:
    """
    Build the messages list for Ollama's /api/chat endpoint.
    Format:
        [
            {"role": "system", "content": "<system prompt>\\n\\nCONTEXT:\\n<context>"},
            {"role": "user",   "content": "<question>"},
        ]

    : Implement this function.
    Steps:
      1. Join chunks into a context string, labelling each with its source filename
      2. Build the system message combining SYSTEM_PROMPT + context
      3. Return [system_message, user_message]
    """
    #: implement
    context_parts = []

    for chunk in chunks:
        source = chunk["metadata"]["source"]

        context_parts.append(
            f"[Source: {source}]\n{chunk['text']}"
        )

    context = "\n\n".join(context_parts)

    system_message = (
        f"{SYSTEM_PROMPT}\n\n"
        f"CONTEXT:\n{context}"
    )

    return [
        {"role": "system", 
         "content": system_message},
        
        {"role": "user",   
         "content": question},
    ]


# ── 4. Generation ──────────────────────────────────────────────────────────

def generate(messages: list[dict]) -> str:
    """
    Send messages to Ollama's /api/chat endpoint and return the response text.
    Uses settings.ollama_url and settings.model_name.

    : Implement this function.
    Steps:
      1. requests.post(settings.ollama_url + "/api/chat", json={...})
      2. Payload: {"model": settings.model_name, "messages": messages, "stream": False}
      3. Parse response.json()["message"]["content"]
      4. Handle requests.exceptions.ConnectionError gracefully
    """
    #: implement
    url = f"{settings.ollama_url}/api/chat"

    payload = {
        "model": settings.model_name,
        "messages": messages,
        "stream": False,
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=120,
        )

        response.raise_for_status()

        data = response.json()

        return data["message"]["content"]

    except requests.exceptions.ConnectionError:
        return (
            "Ollama is not connected. "
            "Please make sure the Ollama service is running."
        )

    except requests.exceptions.RequestException as error:
        return f"Ollama request failed: {error}"

    except (KeyError, ValueError):
        return "Ollama returned an unexpected response."


# ── 5. Confidence scoring ──────────────────────────────────────────────────

def compute_confidence(chunks: list[dict]) -> str:
    """
    Return "high", "medium", or "low" based on the best (lowest) distance score.

    Suggested thresholds (adjust to taste):
        distance < 0.5  → "high"
        distance < 1.0  → "medium"
        otherwise       → "low"

    Return "low" if chunks is empty.

    : Implement this function.
    """
    if not chunks:
        return "low"

    best_distance = min(
        chunk["distance"]
        for chunk in chunks
    )

    if best_distance < 0.5:
        return "high"

    if best_distance < 1.0:
        return "medium"

    return "low"


# ── Quick test (run as a script) ───────────────────────────────────────────

if __name__ == "__main__":
    docs = load_documents("./docs")
    
    print(f"Loaded {len(docs)} chunks from ./docs")

    if docs:
        collection.upsert(
            documents=[d["text"] for d in docs],
            metadatas=[d["metadata"] for d in docs],
            ids=[d["id"] for d in docs],
        )
        # Ingest into ChromaDB
        # collection.upsert(
        #     documents=[d["text"] for d in docs],
        #     metadatas=[d["metadata"] for d in docs],
        #     ids=[d["id"] for d in docs],
        # )
        print(f"Stored {len(docs)} chunks in ChromaDB.")

        question = "What is Python?"

        chunks = retrieve(
            question,
            n_results=settings.max_results,
            max_distance=settings.confidence_threshold,
        )

        print(f"\nRetrieved {len(chunks)} chunks.")

        for chunk in chunks:
            print("\n--- Retrieved chunk ---")
            print("Source:", chunk["metadata"]["source"])
            print("Distance:", chunk["distance"])
            print("Text:", chunk["text"][:200])

        confidence = compute_confidence(chunks)

        print("\nConfidence:", confidence)

        messages = build_prompt(question, chunks)

        print("\nGenerating answer...")

        answer = generate(messages)

        print("\nAnswer:")
        print(answer)