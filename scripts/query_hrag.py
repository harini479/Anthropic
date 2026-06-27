"""
Interactive CLI for querying the H-RAG knowledge base.

Usage:
    python scripts/query_hrag.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from src.config import validate_config
from src.query import query_hrag

console = Console()


def display_result(result: dict) -> None:
    """Pretty-print a query result."""
    retrieval = result["retrieval"]

    # Show retrieval path
    folders = retrieval.get("matched_folders", [])
    files = retrieval.get("matched_files", [])
    chunks = retrieval.get("chunks", [])

    console.print(
        f"\n[dim]Retrieval: {len(folders)} folders → "
        f"{len(files)} docs → {len(chunks)} chunks[/dim]"
    )

    # Show matched folders
    if folders:
        console.print(f"[dim]Folders: {', '.join(folders)}[/dim]")

    # Show matched documents
    if files:
        console.print(f"[dim]Documents: {', '.join(os.path.basename(f) for f in files)}[/dim]")

    # Show the answer
    console.print()
    console.print(Panel(
        Markdown(result["answer"]),
        title="[bold green]Answer[/bold green]",
        border_style="green",
        padding=(1, 2),
    ))


def main():
    console.print(Panel(
        "[bold cyan]H-RAG Query Engine[/bold cyan]\n"
        "[dim]Hierarchical RAG over Anthropic documentation[/dim]\n\n"
        "Type your question and press Enter.\n"
        "Type [bold]quit[/bold] or [bold]exit[/bold] to stop.",
        border_style="cyan",
    ))

    try:
        validate_config()
    except EnvironmentError as e:
        console.print(f"\n[red]❌ Configuration error:[/red]\n{e}")
        sys.exit(1)

    while True:
        try:
            console.print()
            query = console.input("[bold cyan]Ask:[/bold cyan] ").strip()

            if not query:
                continue
            if query.lower() in ("quit", "exit", "q"):
                console.print("[dim]Goodbye! 👋[/dim]")
                break

            with console.status("[bold green]Searching through hierarchy..."):
                result = query_hrag(query)

            display_result(result)

        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye! 👋[/dim]")
            break
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")


if __name__ == "__main__":
    main()
