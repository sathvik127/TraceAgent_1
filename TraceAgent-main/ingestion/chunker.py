"""
TRACE-102: Semantic Text Chunker
==================================
Splits sanitized SRS text into overlapping semantic chunks
using LangChain's RecursiveCharacterTextSplitter.

Sprint plan spec:
  chunk_size=500  (characters)
  chunk_overlap=50 (characters)
"""

from typing import Any
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
CHUNK_SIZE = 500          # characters per chunk
CHUNK_OVERLAP = 50        # overlap between consecutive chunks

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    length_function=len,
    # Prefer splitting on paragraph, then sentence, then word boundaries
    separators=["\n\n", "\n", ". ", " ", ""],
)


def chunk_text(text: str) -> list[dict[str, Any]]:
    """
    Split sanitized SRS text into overlapping chunks.

    Args:
        text: Sanitized SRS body text from the extractor.

    Returns:
        List of chunk dicts:
        [
            {
                "chunk_index": int,
                "text": str,
                "char_count": int,
            },
            ...
        ]
    """
    if not text or not text.strip():
        return []

    raw_chunks: list[str] = _splitter.split_text(text)

    return [
        {
            "chunk_index": i,
            "text": chunk,
            "char_count": len(chunk),
        }
        for i, chunk in enumerate(raw_chunks)
    ]
