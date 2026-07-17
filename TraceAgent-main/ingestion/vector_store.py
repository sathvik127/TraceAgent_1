"""
TRACE-102: Vector Store — FAISS (local) + Pinecone (production)
================================================================
Factory-controlled by environment variable USE_LOCAL_VECTOR_DB:
  - "true"  → FAISSVectorStore  (default, no Pinecone key needed)
  - "false" → PineconeVectorStore (requires PINECONE_API_KEY)

FAISS index and metadata are persisted to:
  data/faiss_index/index.faiss
  data/faiss_index/metadata.pkl

The metadata schema per chunk:
  {
      "Requirement_ID":   str,   # e.g. "doc_chunk_0"
      "chunk_index":      int,
      "source_document":  str,
      "page_number":      int | None,
      "text":             str,
  }
"""

import logging
import os
import pickle
from pathlib import Path
from typing import Any

import numpy as np
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

USE_LOCAL = os.getenv("USE_LOCAL_VECTOR_DB", "true").strip().lower() == "true"
FAISS_INDEX_DIR = Path("data/faiss_index")
EMBEDDING_DIM = 1024   # BGE-M3 output dimension


# ─────────────────────────────────────────────
# FAISS Implementation
# ─────────────────────────────────────────────

class FAISSVectorStore:
    """
    Local FAISS vector store backed by flat L2 index.
    Persists index + metadata to disk for durability across restarts.
    """

    def __init__(self, index_dir: Path | None = None) -> None:
        import faiss  # lazy import — not always installed in prod

        self._faiss = faiss
        self.index_dir = index_dir if index_dir is not None else FAISS_INDEX_DIR
        self.index_dir.mkdir(parents=True, exist_ok=True)

        self._index_path = self.index_dir / "index.faiss"
        self._meta_path = self.index_dir / "metadata.pkl"

        # Load existing or create fresh index
        if self._index_path.exists() and self._meta_path.exists():
            self.index = faiss.read_index(str(self._index_path))
            with open(self._meta_path, "rb") as f:
                self.metadata: list[dict[str, Any]] = pickle.load(f)
            logger.info(
                "Loaded existing FAISS index (%d vectors) from %s",
                self.index.ntotal,
                self.index_dir,
            )
        else:
            self.index = faiss.IndexFlatL2(EMBEDDING_DIM)
            self.metadata = []
            logger.info("Created fresh FAISS index (dim=%d)", EMBEDDING_DIM)

    def upsert_chunks(
        self,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
        doc_metadata: dict[str, Any],
    ) -> int:
        """
        Upsert chunk embeddings + metadata into the FAISS index.

        Args:
            chunks:       List of chunk dicts from chunker (chunk_index, text, …)
            embeddings:   Parallel list of float vectors (1024-dim each)
            doc_metadata: Document-level metadata dict (filename, page_count, …)

        Returns:
            Number of vectors added.
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Chunk/embedding count mismatch: {len(chunks)} vs {len(embeddings)}"
            )

        vectors = np.array(embeddings, dtype=np.float32)
        self.index.add(vectors)

        source_doc = doc_metadata.get("filename", "unknown")
        page_count = doc_metadata.get("page_count")

        for chunk in chunks:
            self.metadata.append(
                {
                    "Requirement_ID": f"{source_doc}_chunk_{chunk['chunk_index']}",
                    "chunk_index": chunk["chunk_index"],
                    "source_document": source_doc,
                    "page_number": page_count,   # page-level granularity not available after merge
                    "text": chunk["text"],
                }
            )

        self._save()
        logger.info("Upserted %d vectors into FAISS index", len(chunks))
        return len(chunks)

    def search(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[dict[str, Any]]:
        """
        Semantic search: returns top_k nearest chunks by L2 distance.

        Returns list of dicts: {metadata..., score (L2 distance), rank}
        """
        if self.index.ntotal == 0:
            return []

        query = np.array([query_embedding], dtype=np.float32)
        distances, indices = self.index.search(query, min(top_k, self.index.ntotal))

        results = []
        for rank, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx == -1:
                continue
            entry = dict(self.metadata[idx])
            entry["score"] = float(dist)
            entry["rank"] = rank + 1
            results.append(entry)
        return results

    def get_all_metadata(self) -> list[dict[str, Any]]:
        """Return all stored metadata records (for Direction B iteration)."""
        return list(self.metadata)

    def _save(self) -> None:
        """Persist index and metadata to disk."""
        self._faiss.write_index(self.index, str(self._index_path))
        with open(self._meta_path, "wb") as f:
            pickle.dump(self.metadata, f)
        logger.debug("FAISS index saved to %s", self.index_dir)


# ─────────────────────────────────────────────
# Pinecone Implementation (production stub)
# ─────────────────────────────────────────────

class PineconeVectorStore:
    """
    Pinecone cloud vector store.
    Requires PINECONE_API_KEY and PINECONE_ENV in environment.
    Dimension is set to 1024 (BGE-M3).
    """

    INDEX_NAME = "traceagent-srs"
    DIMENSION = 1024
    METRIC = "cosine"

    def __init__(self) -> None:
        from pinecone import Pinecone, ServerlessSpec  # lazy import

        api_key = os.getenv("PINECONE_API_KEY", "")
        environment = os.getenv("PINECONE_ENV", "us-east-1")

        if not api_key or api_key == "your_pinecone_api_key_here":
            raise EnvironmentError(
                "PINECONE_API_KEY is not configured. "
                "Set it in .env or use USE_LOCAL_VECTOR_DB=true for local dev."
            )

        pc = Pinecone(api_key=api_key)

        # Create index if it doesn't exist
        existing = [idx.name for idx in pc.list_indexes()]
        if self.INDEX_NAME not in existing:
            pc.create_index(
                name=self.INDEX_NAME,
                dimension=self.DIMENSION,
                metric=self.METRIC,
                spec=ServerlessSpec(cloud="aws", region=environment),
            )
            logger.info("Created Pinecone index '%s'", self.INDEX_NAME)

        self._index = pc.Index(self.INDEX_NAME)
        logger.info("Connected to Pinecone index '%s'", self.INDEX_NAME)

    def upsert_chunks(
        self,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
        doc_metadata: dict[str, Any],
    ) -> int:
        """Upsert to Pinecone with structured metadata."""
        source_doc = doc_metadata.get("filename", "unknown")

        vectors = []
        for chunk, embedding in zip(chunks, embeddings):
            req_id = f"{source_doc}_chunk_{chunk['chunk_index']}"
            vectors.append(
                {
                    "id": req_id,
                    "values": embedding,
                    "metadata": {
                        "Requirement_ID": req_id,
                        "chunk_index": chunk["chunk_index"],
                        "source_document": source_doc,
                        "page_number": doc_metadata.get("page_count"),
                        "text": chunk["text"],
                    },
                }
            )

        # Pinecone upsert in batches of 100
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            self._index.upsert(vectors=vectors[i : i + batch_size])

        logger.info("Upserted %d vectors into Pinecone index '%s'", len(vectors), self.INDEX_NAME)
        return len(vectors)

    def search(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[dict[str, Any]]:
        """Semantic search against Pinecone index."""
        results = self._index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
        )
        return [
            {**match["metadata"], "score": match["score"], "rank": rank + 1}
            for rank, match in enumerate(results.get("matches", []))
        ]

    def get_all_metadata(self) -> list[dict[str, Any]]:
        """
        Fetch all stored requirement metadata.
        NOTE: Pinecone does not support full table scans natively;
        this uses the list + fetch API (requires Pinecone v3+).
        """
        all_meta = []
        for ids_batch in self._index.list(prefix=""):
            fetched = self._index.fetch(ids=ids_batch)
            for vid, vec in fetched["vectors"].items():
                all_meta.append(vec.get("metadata", {}))
        return all_meta


# ─────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────

def get_vector_store() -> FAISSVectorStore | PineconeVectorStore:
    """
    Return the appropriate vector store based on USE_LOCAL_VECTOR_DB env flag.

    USE_LOCAL_VECTOR_DB=true  → FAISSVectorStore  (default)
    USE_LOCAL_VECTOR_DB=false → PineconeVectorStore
    """
    if USE_LOCAL:
        logger.info("Using LOCAL vector store (FAISS)")
        return FAISSVectorStore()
    else:
        logger.info("Using PRODUCTION vector store (Pinecone)")
        return PineconeVectorStore()
