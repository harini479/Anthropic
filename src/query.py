"""
H-RAG Query Engine — Hierarchical retrieval + answer generation.
Queries flow: folders -> docs -> chunks -> LLM answer.
Uses configurable system prompt from system_prompt.txt.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Any

from openai import OpenAI

from src.config import (
    OPENAI_API_KEY,
    TOP_K_FOLDERS,
    TOP_K_DOCS,
    TOP_K_CHUNKS,
    PROJECT_ROOT,
    SIMILARITY_THRESHOLD,
)
from src.embedder import embed_single
from src.db import (
    search_folder_summaries_multi,
    search_doc_summaries_multi,
    search_chunks_multi,
)

# Lazy-initialized client
_client: OpenAI | None = None

# System prompt file path
SYSTEM_PROMPT_PATH = PROJECT_ROOT / "system_prompt.txt"


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def load_system_prompt() -> str:
    """
    Load the system prompt from system_prompt.txt.
    Falls back to a default if the file doesn't exist.
    """
    if SYSTEM_PROMPT_PATH.exists():
        return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()

    # Fallback default
    return (
        "You are a knowledgeable assistant. Answer ONLY using the provided context. "
        "If the context is insufficient, say so clearly. "
        "Cite sources as [Source: filename] for every factual claim."
    )


def save_system_prompt(prompt: str) -> None:
    """Save a new system prompt to system_prompt.txt."""
    SYSTEM_PROMPT_PATH.write_text(prompt, encoding="utf-8")


def hierarchical_retrieve(
    query: str,
    nodes: List[str] = ["anthropic", "projects"],
    top_k_folders: int | None = None,
    top_k_docs: int | None = None,
    top_k_chunks: int | None = None,
) -> Dict[str, Any]:
    """
    Perform hierarchical retrieval through the H-RAG layers across given nodes.
    """
    k_folders = top_k_folders or TOP_K_FOLDERS
    k_docs = top_k_docs or TOP_K_DOCS
    k_chunks = top_k_chunks or TOP_K_CHUNKS

    # Step 1: Embed the query
    query_embedding = embed_single(query)

    # Step 2: Find relevant folders
    folder_results = search_folder_summaries_multi(query_embedding, nodes, top_k=k_folders)
    matched_folders = [r["folder_path"] for r in folder_results]

    # Step 3: Find relevant documents within those folders
    if matched_folders:
        doc_results = search_doc_summaries_multi(query_embedding, nodes, matched_folders, top_k=k_docs)
    else:
        doc_results = []
    matched_files = [r["file_path"] for r in doc_results]

    # Step 4: Find relevant chunks within those documents
    if matched_files:
        chunk_results = search_chunks_multi(query_embedding, nodes, matched_files, top_k=k_chunks)
    else:
        chunk_results = []

    # Step 5: Filter chunks by similarity threshold (Zero Hallucination Guard)
    valid_chunks = [c for c in chunk_results if c.get("similarity", 0) >= SIMILARITY_THRESHOLD]

    return {
        "query": query,
        "folders": folder_results,
        "documents": doc_results,
        "chunks": valid_chunks,
        "matched_folders": matched_folders,
        "matched_files": matched_files,
    }


def generate_answer(
    query: str,
    retrieval_results: Dict[str, Any],
    system_prompt_override: str | None = None,
) -> str:
    """
    Generate an answer using retrieved chunks as context.
    Uses the configurable system prompt from system_prompt.txt.
    """
    client = _get_client()

    chunks = retrieval_results.get("chunks", [])
    if not chunks:
        return ("The provided knowledge base does not contain sufficient information "
                "to answer this question. No relevant context was retrieved (similarity threshold not met).")

    # Build context from chunks with source attribution and node tags
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("metadata", {}).get("file_name", chunk.get("file_path", "unknown"))
        folder = chunk.get("metadata", {}).get("folder", "")
        similarity = chunk.get("similarity", 0)
        node_tag = chunk.get("node", "anthropic").upper()
        context_parts.append(
            f"[Source {i}: {node_tag} NODE | {folder}/{source} | Relevance: {similarity:.3f}]\n{chunk['content']}"
        )

    context = "\n\n---\n\n".join(context_parts)

    # Build the retrieval path for transparency
    folders = retrieval_results.get("matched_folders", [])
    files = retrieval_results.get("matched_files", [])
    retrieval_path = (
        f"Retrieval path: {len(folders)} folders -> "
        f"{len(files)} documents -> {len(chunks)} chunks"
    )

    # Load system prompt (from file or override)
    system_prompt = system_prompt_override or load_system_prompt()

    user_prompt = f"""Question: {query}

{retrieval_path}

Context from knowledge base:
{context}

Answer the question based strictly on the context above. Cite sources using [Source: filename] format."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=1500,
        temperature=0.1,  # Low temp for deterministic, grounded answers
    )

    return response.choices[0].message.content.strip()


def query_hrag(
    query: str,
    nodes: List[str] | None = None,
    top_k_folders: int | None = None,
    top_k_docs: int | None = None,
    top_k_chunks: int | None = None,
    system_prompt_override: str | None = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Full H-RAG query pipeline: retrieve + generate.

    Returns a dict with:
      - answer: The generated answer
      - retrieval: Full retrieval results for inspection
    """
    if nodes is None:
        nodes = ["anthropic", "projects"]

    retrieval = hierarchical_retrieve(
        query, nodes, top_k_folders, top_k_docs, top_k_chunks
    )

    answer = generate_answer(query, retrieval, system_prompt_override)

    return {
        "query": query,
        "answer": answer,
        "retrieval": retrieval,
    }
