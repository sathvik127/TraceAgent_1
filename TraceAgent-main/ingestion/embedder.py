"""
TRACE-102: Embedder — BGE-M3 via OpenRouter
============================================
Converts text chunks into 1024-dimensional dense vectors
using the BAAI/bge-m3 model served through OpenRouter.

Features:
  - Exponential backoff retry on HTTP 429 (rate limit), max 3 retries
  - Batched requests to stay within API limits
  - Returns List[List[float]] aligned with input chunks
"""

import logging
import os
import time
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
EMBEDDING_MODEL: str = "BAAI/bge-m3"          # 1024-dim output
OPENROUTER_EMBED_URL: str = "https://openrouter.ai/api/v1/embeddings"
EMBEDDING_DIM: int = 1024

MAX_RETRIES: int = 3
BASE_BACKOFF: float = 1.0   # seconds; doubles each retry
BATCH_SIZE: int = 32        # chunks per API call


# ─────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────

def _embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Call OpenRouter embeddings API for a single batch of texts.
    Applies exponential backoff on HTTP 429.

    Raises:
        RuntimeError: if all retries exhausted or a non-retryable error occurs.
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://traceagent.local",   # required by OpenRouter
        "X-Title": "TraceAgent",
    }
    payload: dict[str, Any] = {
        "model": EMBEDDING_MODEL,
        "input": texts,
    }

    backoff = BASE_BACKOFF
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(
                OPENROUTER_EMBED_URL,
                headers=headers,
                json=payload,
                timeout=60,
            )

            if response.status_code == 429:
                if attempt == MAX_RETRIES:
                    raise RuntimeError(
                        f"OpenRouter rate limit hit after {MAX_RETRIES} retries."
                    )
                logger.warning(
                    "Rate limit (429) on attempt %d/%d — backing off %.1fs",
                    attempt, MAX_RETRIES, backoff,
                )
                time.sleep(backoff)
                backoff *= 2
                continue

            response.raise_for_status()
            data = response.json()

            # OpenAI-compatible response: {"data": [{"embedding": [...], "index": 0}, ...]}
            embeddings_raw: list[dict] = sorted(
                data["data"], key=lambda x: x["index"]
            )
            return [item["embedding"] for item in embeddings_raw]

        except requests.exceptions.Timeout:
            if attempt == MAX_RETRIES:
                raise RuntimeError("OpenRouter embedding request timed out after max retries.")
            logger.warning("Timeout on attempt %d/%d — retrying...", attempt, MAX_RETRIES)
            time.sleep(backoff)
            backoff *= 2

    # Should never reach here
    raise RuntimeError("Embedding failed after exhausting all retries.")


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of text strings using BGE-M3 via OpenRouter.

    Splits input into batches of BATCH_SIZE to stay within API limits.
    Each output vector has EMBEDDING_DIM (1024) dimensions.

    Args:
        texts: List of text strings to embed (e.g. chunk['text'] values).

    Returns:
        List of float vectors, one per input text, in the same order.

    Raises:
        ValueError: if OPENROUTER_API_KEY is not configured.
        RuntimeError: if embedding fails after retries.
    """
    if not OPENROUTER_API_KEY:
        raise ValueError(
            "OPENROUTER_API_KEY is not set. Please configure it in your .env file."
        )
    if not texts:
        return []

    all_embeddings: list[list[float]] = []

    for batch_start in range(0, len(texts), BATCH_SIZE):
        batch = texts[batch_start : batch_start + BATCH_SIZE]
        logger.info(
            "Embedding batch %d–%d of %d texts",
            batch_start + 1,
            min(batch_start + BATCH_SIZE, len(texts)),
            len(texts),
        )
        batch_embeddings = _embed_batch(batch)
        all_embeddings.extend(batch_embeddings)

    return all_embeddings
