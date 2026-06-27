"""
H-RAG Builder — Orchestration pipeline.
Coordinates the full build: load → chunk → summarize → embed → store.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.config import validate_config, SOURCE_PATH, PROJECTS_PATH
from src.loader import load_documents, get_folder_groups, Document
from src.chunker import chunk_documents, Chunk
from src.summarizer import summarize_documents, summarize_folders, summarize_collection
from src.embedder import embed_texts, embed_single
from src.db import (
    insert_collection_summary,
    insert_folder_summary,
    insert_doc_summary,
    insert_chunks_batch,
    clear_all_tables,
    clear_node_tables,
    get_table_counts,
)
from pathlib import Path

console = Console()


def _make_id(*parts: str) -> str:
    """Create a short deterministic ID from string parts."""
    raw = ":".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def build_hrag(force: bool = False, node_name: str = "anthropic", source_path: Path | None = None) -> None:
    """
    Run the full H-RAG build pipeline.

    Args:
        force: If True, clear existing data for this node before rebuilding.
        node_name: The node identifier ('anthropic' or 'projects').
        source_path: The root directory to load files from.
    """
    console.print(f"\n[bold cyan]=== H-RAG Builder ({node_name.upper()} NODE) ===[/bold cyan]\n")

    if source_path is None:
        source_path = SOURCE_PATH if node_name == "anthropic" else PROJECTS_PATH

    # ── Step 0: Validate config ──────────────────────────────────────────
    with console.status("[bold green]Validating configuration..."):
        validate_config()
    console.print("[green]OK[/green] Configuration valid\n")

    # ── Step 0.5: Clear if force rebuild ─────────────────────────────────
    if force:
        with console.status(f"[bold yellow]Clearing existing data for node '{node_name}'..."):
            clear_node_tables(node_name)
        console.print(f"[yellow]OK[/yellow] Tables cleared for node '{node_name}'\n")

    # ── Step 1: Load documents ───────────────────────────────────────────
    with console.status(f"[bold green]Loading documents from {source_path.name}/..."):
        documents = load_documents(source_path, node_name)
        folder_groups = get_folder_groups(documents)

    console.print(f"[green]OK[/green] Loaded [bold]{len(documents)}[/bold] documents "
                  f"from [bold]{len(folder_groups)}[/bold] folders\n")

    for folder, docs in folder_groups.items():
        console.print(f"  > {folder}")
        for doc in docs:
            console.print(f"     - {doc.metadata['file_name']} "
                          f"({doc.metadata['char_count']:,} chars)")
    console.print()

    # ── Step 2: Chunk documents ──────────────────────────────────────────
    with console.status("[bold green]Chunking documents..."):
        chunks = chunk_documents(documents)

    console.print(f"[green]OK[/green] Created [bold]{len(chunks)}[/bold] chunks\n")

    # ── Step 3: Generate document summaries ──────────────────────────────
    console.print("[bold green]Generating document summaries...[/bold green]")
    doc_summaries: Dict[str, str] = {}
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Summarizing...", total=len(documents))
        for doc in documents:
            from src.summarizer import summarize_document
            file_path = doc.metadata["file_path"]
            progress.update(task, description=f"  Summarizing {doc.metadata['file_name']}...")
            doc_summaries[file_path] = summarize_document(doc)
            progress.advance(task)

    console.print(f"[green]OK[/green] Generated [bold]{len(doc_summaries)}[/bold] document summaries\n")

    # ── Step 4: Generate folder summaries ────────────────────────────────
    console.print("[bold green]Generating folder summaries...[/bold green]")
    folder_summaries = summarize_folders(folder_groups, doc_summaries)
    console.print(f"[green]OK[/green] Generated [bold]{len(folder_summaries)}[/bold] folder summaries\n")

    # ── Step 5: Generate collection summary ──────────────────────────────
    with console.status("[bold green]Generating collection summary..."):
        collection_summary = summarize_collection(folder_summaries)
    console.print(f"[green]OK[/green] Generated collection summary\n")

    # ── Step 6: Embed everything ─────────────────────────────────────────
    console.print("[bold green]Generating embeddings...[/bold green]")

    # 6a. Embed chunks
    with console.status(f"  Embedding {len(chunks)} chunks..."):
        chunk_texts = [c.content for c in chunks]
        chunk_embeddings = embed_texts(chunk_texts)
    console.print(f"  [green]OK[/green] Embedded {len(chunks)} chunks")

    # 6b. Embed document summaries
    with console.status(f"  Embedding {len(doc_summaries)} document summaries..."):
        doc_summary_texts = list(doc_summaries.values())
        doc_summary_embeddings = embed_texts(doc_summary_texts)
    console.print(f"  [green]OK[/green] Embedded {len(doc_summaries)} document summaries")

    # 6c. Embed folder summaries
    with console.status(f"  Embedding {len(folder_summaries)} folder summaries..."):
        folder_summary_texts = list(folder_summaries.values())
        folder_summary_embeddings = embed_texts(folder_summary_texts)
    console.print(f"  [green]OK[/green] Embedded {len(folder_summaries)} folder summaries")

    # 6d. Embed collection summary
    with console.status("  Embedding collection summary..."):
        collection_embedding = embed_single(collection_summary)
    console.print(f"  [green]OK[/green] Embedded collection summary\n")

    # ── Step 7: Store in Supabase ────────────────────────────────────────
    console.print("[bold green]Storing in Supabase...[/bold green]")

    # 7a. Store collection summary
    insert_collection_summary(
        summary_id=_make_id("collection", node_name),
        content=collection_summary,
        embedding=collection_embedding,
        metadata={"name": f"{node_name.capitalize()} Documentation", "doc_count": len(documents)},
        node=node_name,
    )
    console.print("  [green]OK[/green] Stored collection summary")

    # 7b. Store folder summaries
    folder_paths = list(folder_summaries.keys())
    for i, folder_path in enumerate(folder_paths):
        insert_folder_summary(
            folder_id=_make_id("folder", node_name, folder_path),
            folder_path=folder_path,
            content=folder_summaries[folder_path],
            embedding=folder_summary_embeddings[i],
            metadata={
                "folder_path": folder_path,
                "doc_count": len(folder_groups[folder_path]),
            },
            node=node_name,
        )
    console.print(f"  [green]OK[/green] Stored {len(folder_summaries)} folder summaries")

    # 7c. Store document summaries
    doc_paths = list(doc_summaries.keys())
    for i, file_path in enumerate(doc_paths):
        # Find the document to get its metadata
        doc = next(d for d in documents if d.metadata["file_path"] == file_path)
        insert_doc_summary(
            doc_id=doc.doc_id,
            folder_path=doc.metadata["folder_path"],
            file_path=file_path,
            content=doc_summaries[file_path],
            embedding=doc_summary_embeddings[i],
            metadata={
                "file_name": doc.metadata["file_name"],
                "folder": doc.metadata["folder"],
                "char_count": doc.metadata["char_count"],
            },
            node=node_name,
        )
    console.print(f"  [green]OK[/green] Stored {len(doc_summaries)} document summaries")

    # 7d. Store chunks in batches
    chunks_data = []
    for i, chunk in enumerate(chunks):
        chunks_data.append({
            "id": chunk.chunk_id,
            "doc_id": chunk.metadata["doc_id"],
            "folder_path": chunk.metadata["folder_path"],
            "file_path": chunk.metadata["file_path"],
            "content": chunk.content,
            "embedding": chunk_embeddings[i],
            "metadata": {
                "file_name": chunk.metadata["file_name"],
                "folder": chunk.metadata["folder"],
                "chunk_index": chunk.metadata["chunk_index"],
                "total_chunks": chunk.metadata["total_chunks"],
            },
            "node": node_name,
        })

    with console.status(f"  Storing {len(chunks_data)} chunks in batches..."):
        insert_chunks_batch(chunks_data)
    console.print(f"  [green]OK[/green] Stored {len(chunks_data)} chunks\n")

    # ── Final summary ────────────────────────────────────────────────────
    counts = get_table_counts(node_name)
    console.print("[bold cyan]=== Build Complete ===[/bold cyan]\n")
    console.print("[bold]Database contents:[/bold]")
    for table, count in counts.items():
        console.print(f"  * {table}: [bold green]{count}[/bold green] rows")
    console.print()


if __name__ == "__main__":
    build_hrag()
