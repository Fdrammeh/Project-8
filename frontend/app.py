"""
Module 8 Project — Containerized RAG Assistant  
Frontend: Streamlit Chat UI
============================
Run locally:
    BACKEND_URL=http://localhost:8000 streamlit run app.py

Inside Docker Compose: started automatically; reads BACKEND_URL from env.

Your task: implement the four sections below.

Required features:
    1. Session state    — initialise chat_history list before any reads
    2. Sidebar          — health check, document count, Re-index button
    3. Chat display     — render existing messages with st.chat_message()
    4. Chat input       — st.chat_input(), call /ask, append to history

API endpoints to call (all relative to BACKEND_URL):
    GET  /health  — check service status
    POST /ingest  — trigger document re-indexing
    POST /ask     — send question, get {answer, sources, confidence}
"""

import streamlit as st
import requests
import os

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

# ── Step 1: Page configuration ─────────────────────────────────────────────

st.set_page_config(
    page_title="RAG Assistant", 
    page_icon="🔍", 
    layout="centered")

# ── Step 2: Session state initialisation ───────────────────────────────────
# : Initialise "chat_history" as an empty list if it doesn't exist yet.
# Always initialise session state keys before reading them to avoid KeyError.
#
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# ════════════════════════════════════════════════════════════════════════════
# SECTION A — SIDEBAR
# ════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.header("RAG Assistant")
    st.caption("Ask questions about the documents in the RAG knowledge base.")
#   - App title and a brief description
#   - Health check: GET BACKEND_URL + "/health"
#     Show st.success("Backend: connected") or st.error("Backend: unreachable")
#     Show a caption with chromadb status, ollama status, and document count
#   - st.divider()
#   - "Re-index Documents" button:
#     On click: POST BACKEND_URL + "/ingest"
#     Show st.success with the number of chunks ingested, or st.error on failure
    try:
        health_response = requests.get(
            f"{BACKEND_URL}/health",
            timeout=5,
        )

        health_response.raise_for_status()
        health = health_response.json()

        if health["status"] == "ok":
            st.success("Backend: connected")
        else:
            st.warning("Backend: degraded")

        st.caption(
            f"ChromaDB: {health.get('chromadb', 'unknown')} | "
            f"Ollama: {health.get('ollama', 'unknown')}"
        )

        st.caption(
            f"Document chunks: {health.get('document_count', 0)}"
        )

    except requests.exceptions.RequestException:
        st.error("Backend: unreachable")

    st.divider()

    if st.button("Re-index Documents"):
        try:
            ingest_response = requests.post(
                f"{BACKEND_URL}/ingest",
                timeout=30,
            )

            ingest_response.raise_for_status()

            ingest_data = ingest_response.json()

            st.success(
                f"Ingested {ingest_data['chunks_ingested']} chunks."
            )

        except requests.exceptions.RequestException as error:
            st.error(f"Re-index failed: {error}")


# ════════════════════════════════════════════════════════════════════════════
# SECTION B — MAIN CONTENT
# ════════════════════════════════════════════════════════════════════════════
# : 
st.title("RAG Assistant")
st.caption("Ask questions grounded in your documents.")

# ── Chat history display ───────────────────────────────────────────────────
# : Loop over st.session_state.chat_history and render each message.
#
# Each message in history is a dict: {"role": "user"|"assistant", "content": str}
# Use st.chat_message(role) as a context manager:
#
#   for msg in st.session_state.chat_history:
#       with st.chat_message(msg["role"]):
#           st.markdown(msg["content"])
#
# For assistant messages that have a "sources" key, show citations in an expander.
# For assistant messages that have a "confidence" key, show a colour-coded badge.

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        if msg["role"] == "assistant":

            confidence = msg.get("confidence")

            if confidence:
                confidence_colours = {
                    "high": "green",
                    "medium": "orange",
                    "low": "red",
                }

                colour = confidence_colours.get(
                    confidence,
                    "gray",
                )

                st.markdown(
                    f":{colour}[Confidence: **{confidence}**]"
                )

            sources = msg.get("sources", [])

            if sources:
                with st.expander("Sources"):
                    for source in sources:
                        st.markdown(
                            f"**{source['source']}** "
                            f"(distance: {source['distance']:.3f})"
                        )
                        st.write(source["text"])


# ── Chat input ─────────────────────────────────────────────────────────────
# : Use st.chat_input("Ask a question...") to get user input.
# When the user submits a question:
#   1. Append {"role": "user", "content": question} to chat_history
#   2. Display the user message immediately with st.chat_message("user")
#   3. Show a spinner while calling POST BACKEND_URL + "/ask"
#      Payload: {"question": question}
#   4. On success:
#      - Display the answer with st.chat_message("assistant")
#      - Show confidence badge (green=high, orange=medium, red=low)
#      - Show source citations in an st.expander
#      - Append {"role": "assistant", "content": answer, "sources": [...], "confidence": "..."} to chat_history
#   5. On requests.exceptions.ConnectionError:
#      - Show st.error("Cannot reach the backend at ...")
#   6. On HTTP error (e.g. 503 Ollama not running):
#      - Show st.error with the error detail from the response

# ── Hint: colour-coded confidence badge ───────────────────────────────────
# CONFIDENCE_COLOURS = {"high": "green", "medium": "orange", "low": "red"}
# colour = CONFIDENCE_COLOURS.get(confidence, "gray")
# st.markdown(f":{colour}[Confidence: **{confidence}**]")

question = st.chat_input("Ask a question...")

if question:

    st.session_state.chat_history.append(
        {
            "role": "user",
            "content": question,
        }
    )

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):

        with st.spinner("Searching documents and generating an answer..."):

            try:
                response = requests.post(
                    f"{BACKEND_URL}/ask",
                    json={
                        "question": question,
                    },
                    timeout=120,
                )

                response.raise_for_status()

                data = response.json()

                answer = data["answer"]
                sources = data.get("sources", [])
                confidence = data.get("confidence", "low")

                st.markdown(answer)

                confidence_colours = {
                    "high": "green",
                    "medium": "orange",
                    "low": "red",
                }

                colour = confidence_colours.get(
                    confidence,
                    "gray",
                )

                st.markdown(
                    f":{colour}[Confidence: **{confidence}**]"
                )

                if sources:
                    with st.expander("Sources"):
                        for source in sources:
                            st.markdown(
                                f"**{source['source']}** "
                                f"(distance: {source['distance']:.3f})"
                            )
                            st.write(source["text"])

                st.session_state.chat_history.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                        "confidence": confidence,
                    }
                )

            except requests.exceptions.ConnectionError:
                st.error(
                    f"Cannot reach the backend at {BACKEND_URL}"
                )

            except requests.exceptions.HTTPError:
                try:
                    detail = response.json().get(
                        "detail",
                        response.text,
                    )
                except ValueError:
                    detail = response.text

                st.error(
                    f"Backend error: {detail}"
                )

            except requests.exceptions.RequestException as error:
                st.error(
                    f"Request failed: {error}"
                )