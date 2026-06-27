"""
Hierarchical summarizer for H-RAG pipeline.
Uses OpenAI GPT to generate summaries at 3 levels:
  1. Document summaries
  2. Folder summaries (from document summaries)
  3. Collection summary (from folder summaries)
"""

from __future__ import annotations

from typing import Dict, List

from openai import OpenAI

from src.config import OPENAI_API_KEY
from src.loader import Document


# Lazy-initialized client
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def _call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
    """Make a chat completion call to OpenAI."""
    client = _get_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


# ── Level 1: Document Summaries ──────────────────────────────────────────────

DOCUMENT_SUMMARY_SYSTEM = """You are a technical documentation summarizer. 
Create a concise, information-dense summary of the given document. 
Focus on the key concepts, techniques, and topics covered.
Keep it under 200 words. Be specific — mention tool names, API concepts, and technical terms."""


def summarize_document(document: Document) -> str:
    """Generate a summary for a single document."""
    # Truncate very long documents to fit context
    content = document.content[:12000]

    user_prompt = (
        f"Document: {document.metadata.get('file_name', 'unknown')}\n"
        f"Folder: {document.metadata.get('folder', 'root')}\n\n"
        f"Content:\n{content}"
    )

    return _call_llm(DOCUMENT_SUMMARY_SYSTEM, user_prompt)


def summarize_documents(documents: List[Document]) -> Dict[str, str]:
    """
    Generate summaries for all documents.
    Returns a dict mapping file_path -> summary text.
    """
    summaries: Dict[str, str] = {}
    for doc in documents:
        file_path = doc.metadata["file_path"]
        summaries[file_path] = summarize_document(doc)
    return summaries


# ── Level 2: Folder Summaries ────────────────────────────────────────────────

FOLDER_SUMMARY_SYSTEM = """You are a technical documentation summarizer.
Given summaries of all documents within a folder, create a concise overview 
of what this folder covers as a collection of knowledge.
Focus on the main themes, topics, and how the documents relate to each other.
Keep it under 150 words."""


def summarize_folder(
    folder_path: str,
    doc_summaries: Dict[str, str],
) -> str:
    """
    Generate a summary for a folder based on its document summaries.

    Args:
        folder_path: The folder path identifier.
        doc_summaries: Dict mapping file_path -> summary for docs in this folder.
    """
    docs_text = "\n\n".join(
        f"--- {path} ---\n{summary}"
        for path, summary in doc_summaries.items()
    )

    user_prompt = (
        f"Folder: {folder_path}\n"
        f"Number of documents: {len(doc_summaries)}\n\n"
        f"Document Summaries:\n{docs_text}"
    )

    return _call_llm(FOLDER_SUMMARY_SYSTEM, user_prompt)


def summarize_folders(
    folder_groups: Dict[str, List[Document]],
    all_doc_summaries: Dict[str, str],
) -> Dict[str, str]:
    """
    Generate summaries for all folders.
    Returns a dict mapping folder_path -> summary text.
    """
    folder_summaries: Dict[str, str] = {}

    for folder_path, docs in folder_groups.items():
        # Gather document summaries for this folder
        folder_doc_summaries = {
            doc.metadata["file_path"]: all_doc_summaries[doc.metadata["file_path"]]
            for doc in docs
            if doc.metadata["file_path"] in all_doc_summaries
        }
        folder_summaries[folder_path] = summarize_folder(folder_path, folder_doc_summaries)

    return folder_summaries


# ── Level 3: Collection Summary ──────────────────────────────────────────────

COLLECTION_SUMMARY_SYSTEM = """You are a technical documentation summarizer.
Given summaries of all folders in a documentation collection, create a high-level 
overview of what this entire collection covers.
This should help someone quickly understand the scope and topics of the full corpus.
Keep it under 150 words."""


def summarize_collection(folder_summaries: Dict[str, str]) -> str:
    """Generate a single collection-level summary from all folder summaries."""
    folders_text = "\n\n".join(
        f"--- Folder: {path} ---\n{summary}"
        for path, summary in folder_summaries.items()
    )

    user_prompt = (
        f"Collection: Anthropic Documentation\n"
        f"Number of folders: {len(folder_summaries)}\n\n"
        f"Folder Summaries:\n{folders_text}"
    )

    return _call_llm(COLLECTION_SUMMARY_SYSTEM, user_prompt, max_tokens=300)
