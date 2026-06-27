"""
Supabase pgvector database module for H-RAG pipeline.
Manages 4 tables (one per hierarchy level) in Supabase with pgvector.
Now supports Multi-Node architecture.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from supabase import create_client, Client

from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY


# ── Table names for the 4-level hierarchy ────────────────────────────────────
TABLE_COLLECTION_SUMMARIES = "hrag_collection_summaries"
TABLE_FOLDER_SUMMARIES = "hrag_folder_summaries"
TABLE_DOC_SUMMARIES = "hrag_doc_summaries"
TABLE_CHUNKS = "hrag_chunks"

ALL_TABLES = [
    TABLE_COLLECTION_SUMMARIES,
    TABLE_FOLDER_SUMMARIES,
    TABLE_DOC_SUMMARIES,
    TABLE_CHUNKS,
]


# Lazy-initialized client
_client: Client | None = None


def _get_client() -> Client:
    """Get or create the Supabase client."""
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _client


# ── Insert operations ────────────────────────────────────────────────────────


def insert_collection_summary(
    summary_id: str,
    content: str,
    embedding: List[float],
    metadata: Dict[str, Any],
    node: str = "anthropic",
) -> None:
    """Insert a collection-level summary."""
    client = _get_client()
    client.table(TABLE_COLLECTION_SUMMARIES).upsert({
        "id": summary_id,
        "content": content,
        "embedding": embedding,
        "metadata": metadata,
        "node": node,
    }).execute()


def insert_folder_summary(
    folder_id: str,
    folder_path: str,
    content: str,
    embedding: List[float],
    metadata: Dict[str, Any],
    node: str = "anthropic",
) -> None:
    """Insert a folder-level summary."""
    client = _get_client()
    client.table(TABLE_FOLDER_SUMMARIES).upsert({
        "id": folder_id,
        "folder_path": folder_path,
        "content": content,
        "embedding": embedding,
        "metadata": metadata,
        "node": node,
    }).execute()


def insert_doc_summary(
    doc_id: str,
    folder_path: str,
    file_path: str,
    content: str,
    embedding: List[float],
    metadata: Dict[str, Any],
    node: str = "anthropic",
) -> None:
    """Insert a document-level summary."""
    client = _get_client()
    client.table(TABLE_DOC_SUMMARIES).upsert({
        "id": doc_id,
        "folder_path": folder_path,
        "file_path": file_path,
        "content": content,
        "embedding": embedding,
        "metadata": metadata,
        "node": node,
    }).execute()


def insert_chunk(
    chunk_id: str,
    doc_id: str,
    folder_path: str,
    file_path: str,
    content: str,
    embedding: List[float],
    metadata: Dict[str, Any],
    node: str = "anthropic",
) -> None:
    """Insert a single chunk."""
    client = _get_client()
    client.table(TABLE_CHUNKS).upsert({
        "id": chunk_id,
        "doc_id": doc_id,
        "folder_path": folder_path,
        "file_path": file_path,
        "content": content,
        "embedding": embedding,
        "metadata": metadata,
        "node": node,
    }).execute()


def insert_chunks_batch(chunks_data: List[Dict[str, Any]]) -> None:
    """Insert multiple chunks at once. Each dict should have all chunk fields."""
    client = _get_client()
    batch_size = 50
    for i in range(0, len(chunks_data), batch_size):
        batch = chunks_data[i : i + batch_size]
        client.table(TABLE_CHUNKS).upsert(batch).execute()


# ── Search operations (Single Node) ──────────────────────────────────────────

def search_folder_summaries(
    query_embedding: List[float],
    top_k: int = 2,
) -> List[Dict[str, Any]]:
    client = _get_client()
    result = client.rpc("match_folder_summaries", {
        "query_embedding": query_embedding,
        "match_count": top_k,
    }).execute()
    return result.data


def search_doc_summaries(
    query_embedding: List[float],
    folder_paths: List[str],
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    client = _get_client()
    result = client.rpc("match_doc_summaries", {
        "query_embedding": query_embedding,
        "filter_folder_paths": folder_paths,
        "match_count": top_k,
    }).execute()
    return result.data


def search_chunks(
    query_embedding: List[float],
    file_paths: List[str],
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    client = _get_client()
    result = client.rpc("match_chunks", {
        "query_embedding": query_embedding,
        "filter_file_paths": file_paths,
        "match_count": top_k,
    }).execute()
    return result.data


# ── Search operations (Multi-Node) ───────────────────────────────────────────

def search_folder_summaries_multi(
    query_embedding: List[float],
    nodes: List[str],
    top_k: int = 2,
) -> List[Dict[str, Any]]:
    client = _get_client()
    result = client.rpc("match_folder_summaries_multi", {
        "query_embedding": query_embedding,
        "nodes": nodes,
        "match_count": top_k,
    }).execute()
    return result.data


def search_doc_summaries_multi(
    query_embedding: List[float],
    nodes: List[str],
    folder_paths: List[str],
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    client = _get_client()
    result = client.rpc("match_doc_summaries_multi", {
        "query_embedding": query_embedding,
        "nodes": nodes,
        "filter_folder_paths": folder_paths,
        "match_count": top_k,
    }).execute()
    return result.data


def search_chunks_multi(
    query_embedding: List[float],
    nodes: List[str],
    file_paths: List[str],
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    client = _get_client()
    result = client.rpc("match_chunks_multi", {
        "query_embedding": query_embedding,
        "nodes": nodes,
        "filter_file_paths": file_paths,
        "match_count": top_k,
    }).execute()
    return result.data


# ── Utility ──────────────────────────────────────────────────────────────────

def clear_all_tables() -> None:
    """Delete all rows from all H-RAG tables. Use with caution."""
    client = _get_client()
    for table in ALL_TABLES:
        client.table(table).delete().neq("id", "").execute()


def clear_node_tables(node: str) -> None:
    """Delete all rows belonging to a specific node."""
    client = _get_client()
    for table in ALL_TABLES:
        client.table(table).delete().eq("node", node).execute()


def get_table_counts(node: Optional[str] = None) -> Dict[str, int]:
    """Return row counts for all H-RAG tables."""
    client = _get_client()
    counts = {}
    for table in ALL_TABLES:
        query = client.table(table).select("id", count="exact")
        if node:
            query = query.eq("node", node)
        result = query.execute()
        counts[table] = result.count or 0
    return counts
