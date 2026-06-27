"""
Configuration loader for H-RAG pipeline.
Loads environment variables from .env and exposes them as typed constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env from project root ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# ── OpenAI ───────────────────────────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_EMBEDDING_MODEL: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# ── Supabase ─────────────────────────────────────────────────────────────────
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")

# ── Chunking ─────────────────────────────────────────────────────────────────
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))

# ── Source Data ──────────────────────────────────────────────────────────────
SOURCE_FOLDER: str = os.getenv("SOURCE_FOLDER", "Anthropic")
SOURCE_PATH: Path = PROJECT_ROOT / SOURCE_FOLDER

PROJECTS_FOLDER: str = os.getenv("PROJECTS_FOLDER", "projects")
PROJECTS_PATH: Path = PROJECT_ROOT / PROJECTS_FOLDER

# ── Retrieval ────────────────────────────────────────────────────────────────
TOP_K_FOLDERS: int = int(os.getenv("TOP_K_FOLDERS", "2"))
TOP_K_DOCS: int = int(os.getenv("TOP_K_DOCS", "3"))
TOP_K_CHUNKS: int = int(os.getenv("TOP_K_CHUNKS", "5"))
SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.3"))


def validate_config() -> None:
    """Validate that all required configuration values are present."""
    errors = []
    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY is not set in .env")
    if not SUPABASE_URL:
        errors.append("SUPABASE_URL is not set in .env")
    if not SUPABASE_SERVICE_KEY:
        errors.append("SUPABASE_SERVICE_KEY is not set in .env")
    if not SOURCE_PATH.exists():
        errors.append(f"Source folder not found: {SOURCE_PATH}")

    if errors:
        raise EnvironmentError(
            "Configuration errors:\n" + "\n".join(f"  • {e}" for e in errors)
        )
