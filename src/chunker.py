"""
Document chunker for H-RAG pipeline.
Splits documents into overlapping chunks using markdown-aware
or plain-text recursive splitting, preserving parent metadata.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import List

from langchain_text_splitters import (
    MarkdownTextSplitter,
    RecursiveCharacterTextSplitter,
)

from src.config import CHUNK_SIZE, CHUNK_OVERLAP
from src.loader import Document


@dataclass
class Chunk:
    """A chunk of text with inherited document metadata."""
    content: str
    metadata: dict = field(default_factory=dict)

    @property
    def chunk_id(self) -> str:
        """Deterministic ID based on content + source."""
        raw = f"{self.metadata.get('file_path', '')}:{self.metadata.get('chunk_index', 0)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _get_splitter(file_type: str):
    """Return the appropriate splitter based on file type."""
    if file_type == ".md":
        return MarkdownTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )
    else:
        return RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )


def chunk_document(document: Document) -> List[Chunk]:
    """
    Split a single document into chunks.
    Each chunk inherits the parent document's metadata
    plus chunk_index and total_chunks.
    """
    splitter = _get_splitter(document.metadata.get("file_type", ".txt"))
    texts = splitter.split_text(document.content)

    chunks = []
    for i, text in enumerate(texts):
        chunk_metadata = {
            **document.metadata,
            "chunk_index": i,
            "total_chunks": len(texts),
            "doc_id": document.doc_id,
        }
        chunks.append(Chunk(content=text, metadata=chunk_metadata))

    return chunks


def chunk_documents(documents: List[Document]) -> List[Chunk]:
    """
    Split all documents into chunks.
    Returns a flat list of all Chunk objects.
    """
    all_chunks: List[Chunk] = []
    for doc in documents:
        doc_chunks = chunk_document(doc)
        all_chunks.extend(doc_chunks)
    return all_chunks


if __name__ == "__main__":
    from src.loader import load_documents

    docs = load_documents()
    chunks = chunk_documents(docs)
    print(f"Created {len(chunks)} chunks from {len(docs)} documents:")
    for doc in docs:
        doc_chunks = [c for c in chunks if c.metadata["file_path"] == doc.metadata["file_path"]]
        print(f"  {doc.metadata['file_name']}: {len(doc_chunks)} chunks")
