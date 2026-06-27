"""
Embedding module for H-RAG pipeline.
Uses OpenAI's embedding API to generate vector embeddings for text.
"""

from __future__ import annotations

import time
from typing import List

from openai import OpenAI

from src.config import OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL


# Lazy-initialized client
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Get or create the OpenAI client."""
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def embed_texts(
    texts: List[str],
    model: str | None = None,
    batch_size: int = 100,
    retry_delay: float = 1.0,
) -> List[List[float]]:
    """
    Generate embeddings for a list of texts using OpenAI.

    Args:
        texts: List of strings to embed.
        model: Override the embedding model (defaults to env config).
        batch_size: Number of texts per API call (max ~2048 for OpenAI).
        retry_delay: Seconds to wait between retries on rate limit.

    Returns:
        List of embedding vectors (each a list of floats).
    """
    client = _get_client()
    model = model or OPENAI_EMBEDDING_MODEL
    all_embeddings: List[List[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]

        # Retry loop for rate limits
        for attempt in range(5):
            try:
                response = client.embeddings.create(
                    input=batch,
                    model=model,
                )
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                break
            except Exception as e:
                if "rate_limit" in str(e).lower() and attempt < 4:
                    wait = retry_delay * (2 ** attempt)
                    time.sleep(wait)
                else:
                    raise

    return all_embeddings


def embed_single(text: str, model: str | None = None) -> List[float]:
    """Embed a single text string. Convenience wrapper."""
    return embed_texts([text], model=model)[0]


def get_embedding_dimension(model: str | None = None) -> int:
    """
    Return the embedding dimension for the configured model.
    This avoids a round-trip API call for known models.
    """
    model = model or OPENAI_EMBEDDING_MODEL
    dimensions = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }
    return dimensions.get(model, 1536)


if __name__ == "__main__":
    from src.config import validate_config
    validate_config()

    test_texts = [
        "What is the Model Context Protocol?",
        "How do I use tool calling with Claude?",
    ]
    embeddings = embed_texts(test_texts)
    print(f"Generated {len(embeddings)} embeddings")
    print(f"Dimension: {len(embeddings[0])}")
