"""
TRACE-102: End-to-End Ingestion Pipeline
==========================================
Orchestrates the full SRS ingestion flow:
  1. Extract text from PDF/DOCX
  2. Sanitize (done inside extractor)
  3. Chunk with RecursiveCharacterTextSplitter
  4. Embed with BGE-M3 via OpenRouter (with backoff)
  5. Upsert into vector store (FAISS or Pinecone)

Returns a structured pipeline result for the API response.
"""

import logging
from typing import Any

from .chunker import chunk_text
from .embedder import get_embeddings
from .extractor import extract_document
from .vector_store import get_vector_store

logger = logging.getLogger(__name__)


def run_ingestion_pipeline(
    file_bytes: bytes,
    filename: str,
) -> dict[str, Any]:
    """
    Run the full SRS ingestion pipeline for a single uploaded document.

    Args:
        file_bytes: Raw bytes of the uploaded PDF or DOCX file.
        filename:   Original filename (used to determine file type and for metadata).

    Returns:
        {
            "chunks_stored":      int,        # number of vectors upserted
            "failed_pages":       list,       # pages that failed extraction
            "document_metadata":  dict,       # filename, upload_date, page_count, version
            "chunk_preview":      list,       # first 3 chunks for sanity-checking
        }

    Raises:
        ValueError: unsupported file type or empty document
        RuntimeError: embedding or vector store failure
    """
    # ── Step 1: Extract & Sanitize ───────────────────────────────────────────
    logger.info("[Pipeline] Step 1 — Extracting document: %s", filename)
    extraction = extract_document(file_bytes, filename)

    extracted_text: str = extraction["extracted_text"]
    doc_metadata: dict = extraction["document_metadata"]
    failed_pages: list = extraction["failed_pages"]

    if not extracted_text.strip():
        raise ValueError(
            f"Document '{filename}' yielded no extractable text. "
            "It may be fully scanned or corrupt."
        )

    logger.info(
        "[Pipeline] Extracted %d chars from '%s' (%d failed pages)",
        len(extracted_text),
        filename,
        len(failed_pages),
    )

    # ── Step 2: Chunk ────────────────────────────────────────────────────────
    logger.info("[Pipeline] Step 2 — Chunking text")
    chunks = chunk_text(extracted_text)

    if not chunks:
        raise ValueError(f"Document '{filename}' produced zero chunks after splitting.")

    logger.info("[Pipeline] Produced %d chunks", len(chunks))

    # ── Step 3: Embed ────────────────────────────────────────────────────────
    logger.info("[Pipeline] Step 3 — Embedding %d chunks via BGE-M3", len(chunks))
    chunk_texts = [c["text"] for c in chunks]
    embeddings = get_embeddings(chunk_texts)

    logger.info("[Pipeline] Received %d embeddings", len(embeddings))

    # ── Step 4: Upsert ───────────────────────────────────────────────────────
    logger.info("[Pipeline] Step 4 — Upserting into vector store")
    vector_store = get_vector_store()
    chunks_stored = vector_store.upsert_chunks(chunks, embeddings, doc_metadata)

    logger.info("[Pipeline] Pipeline complete — %d chunks stored", chunks_stored)

    return {
        "chunks_stored": chunks_stored,
        "failed_pages": failed_pages,
        "document_metadata": doc_metadata,
        "chunk_preview": chunks[:3],   # first 3 chunks for verification
    }
