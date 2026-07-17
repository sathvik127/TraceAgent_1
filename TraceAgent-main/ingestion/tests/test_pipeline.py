"""
TRACE-102: Integration Test — Full Ingestion Pipeline
======================================================
Verifies the full pipeline end-to-end:
  - Ingest a short 3-requirement dummy SRS
  - Confirm all chunks are stored in the vector DB
  - Confirm metadata fields are correct per chunk

These tests use the FAISS local store (USE_LOCAL_VECTOR_DB=true)
and mock the OpenRouter embedding API to avoid live API calls.

Run with:
    pytest ingestion/tests/test_pipeline.py -v
"""

import os
import io
import pickle
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

DUMMY_SRS_TEXT = """
FR-01: The system shall allow users to register with a unique username and password.

FR-02: The system shall authenticate registered users via a secure login mechanism.
Users who enter incorrect credentials three times shall be temporarily locked out.

FR-03: The system shall display the current account balance to authenticated users.
The balance shall be updated in real-time following any deposit or withdrawal operation.
""".strip()

# Fake 1024-dim embedding (uniform, deterministic)
FAKE_EMBEDDING = [0.01] * 1024


def _make_dummy_docx(text: str) -> bytes:
    """Create a DOCX in memory from plain text."""
    from docx import Document as DocxDocument
    doc = DocxDocument()
    for line in text.split("\n\n"):
        if line.strip():
            doc.add_paragraph(line.strip())
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


@pytest.fixture()
def temp_faiss_dir(tmp_path, monkeypatch):
    """
    Redirect the FAISS index directory to a temp folder so tests
    don't pollute the real data/ directory.
    """
    monkeypatch.setenv("USE_LOCAL_VECTOR_DB", "true")
    import ingestion.vector_store as vs_module
    original_dir = vs_module.FAISS_INDEX_DIR
    vs_module.FAISS_INDEX_DIR = tmp_path / "faiss_index"
    yield tmp_path / "faiss_index"
    vs_module.FAISS_INDEX_DIR = original_dir


# ─────────────────────────────────────────────
# Chunker Tests
# ─────────────────────────────────────────────

class TestChunker:
    def test_produces_chunks(self):
        from ingestion.chunker import chunk_text
        chunks = chunk_text(DUMMY_SRS_TEXT)
        assert len(chunks) >= 1

    def test_each_chunk_has_required_fields(self):
        from ingestion.chunker import chunk_text
        chunks = chunk_text(DUMMY_SRS_TEXT)
        for chunk in chunks:
            assert "chunk_index" in chunk
            assert "text" in chunk
            assert "char_count" in chunk
            assert chunk["char_count"] > 0

    def test_chunk_indices_sequential(self):
        from ingestion.chunker import chunk_text
        chunks = chunk_text(DUMMY_SRS_TEXT)
        for i, chunk in enumerate(chunks):
            assert chunk["chunk_index"] == i

    def test_empty_text_returns_empty(self):
        from ingestion.chunker import chunk_text
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_chunk_respects_max_size(self):
        from ingestion.chunker import chunk_text, CHUNK_SIZE
        chunks = chunk_text(DUMMY_SRS_TEXT)
        for chunk in chunks:
            # Allow small overage due to separator handling
            assert chunk["char_count"] <= CHUNK_SIZE + 100, (
                f"Chunk {chunk['chunk_index']} is too large: {chunk['char_count']} chars"
            )


# ─────────────────────────────────────────────
# FAISS Vector Store Tests
# ─────────────────────────────────────────────

class TestFAISSVectorStore:
    def test_upsert_and_count(self, temp_faiss_dir):
        """Upserted chunks should be counted in the FAISS index."""
        from ingestion.vector_store import FAISSVectorStore

        store = FAISSVectorStore(index_dir=temp_faiss_dir)
        chunks = [
            {"chunk_index": 0, "text": "FR-01: Registration.", "char_count": 20},
            {"chunk_index": 1, "text": "FR-02: Login.", "char_count": 13},
            {"chunk_index": 2, "text": "FR-03: Balance.", "char_count": 15},
        ]
        embeddings = [FAKE_EMBEDDING] * 3
        doc_meta = {"filename": "test_srs.docx", "page_count": None, "upload_date": "2026-01-01"}

        count = store.upsert_chunks(chunks, embeddings, doc_meta)
        assert count == 3
        assert store.index.ntotal == 3

    def test_metadata_fields_correct(self, temp_faiss_dir):
        """Each metadata record must have the required fields with correct values."""
        from ingestion.vector_store import FAISSVectorStore

        store = FAISSVectorStore(index_dir=temp_faiss_dir)
        chunks = [{"chunk_index": 0, "text": "FR-01: Registration.", "char_count": 20}]
        embeddings = [FAKE_EMBEDDING]
        doc_meta = {"filename": "srs.docx", "page_count": 5, "upload_date": "2026-01-01"}

        store.upsert_chunks(chunks, embeddings, doc_meta)

        all_meta = store.get_all_metadata()
        assert len(all_meta) == 1
        record = all_meta[0]

        assert "Requirement_ID" in record
        assert "chunk_index" in record
        assert "source_document" in record
        assert "text" in record
        assert record["source_document"] == "srs.docx"
        assert record["chunk_index"] == 0
        assert "srs.docx_chunk_0" in record["Requirement_ID"]

    def test_search_returns_results(self, temp_faiss_dir):
        """Searching a populated store should return nearest chunks."""
        from ingestion.vector_store import FAISSVectorStore

        store = FAISSVectorStore(index_dir=temp_faiss_dir)
        chunks = [
            {"chunk_index": 0, "text": "FR-01: Registration.", "char_count": 20},
            {"chunk_index": 1, "text": "FR-02: Login.", "char_count": 13},
        ]
        embeddings = [FAKE_EMBEDDING, FAKE_EMBEDDING]
        doc_meta = {"filename": "srs.docx", "page_count": None, "upload_date": "2026-01-01"}
        store.upsert_chunks(chunks, embeddings, doc_meta)

        results = store.search(FAKE_EMBEDDING, top_k=2)
        assert len(results) == 2
        for r in results:
            assert "score" in r
            assert "rank" in r

    def test_persistence(self, temp_faiss_dir):
        """Index persisted to disk should be loadable by a new store instance."""
        from ingestion.vector_store import FAISSVectorStore

        store1 = FAISSVectorStore(index_dir=temp_faiss_dir)
        chunks = [{"chunk_index": 0, "text": "FR-01: Registration.", "char_count": 20}]
        store1.upsert_chunks(chunks, [FAKE_EMBEDDING], {"filename": "srs.docx", "page_count": None})

        # Load fresh instance from same directory
        store2 = FAISSVectorStore(index_dir=temp_faiss_dir)
        assert store2.index.ntotal == 1
        assert len(store2.get_all_metadata()) == 1

    def test_mismatch_raises(self, temp_faiss_dir):
        """Chunk/embedding count mismatch must raise ValueError."""
        from ingestion.vector_store import FAISSVectorStore

        store = FAISSVectorStore(index_dir=temp_faiss_dir)
        with pytest.raises(ValueError, match="mismatch"):
            store.upsert_chunks(
                [{"chunk_index": 0, "text": "x", "char_count": 1}],
                [],   # wrong count
                {"filename": "srs.docx", "page_count": None},
            )


# ─────────────────────────────────────────────
# Full Pipeline Integration Test
# ─────────────────────────────────────────────

class TestPipelineIntegration:
    """
    Integration test: ingest a 3-requirement dummy SRS document through
    the full pipeline (mocking only the OpenRouter embedding API call).
    Verifies all chunks are stored with correct metadata in FAISS.
    """

    def test_full_pipeline_docx(self, temp_faiss_dir, monkeypatch):
        """
        Given a 3-requirement dummy SRS DOCX:
        - Pipeline should extract text, produce chunks, embed, and store all chunks.
        - Returned chunk count must be > 0.
        - All metadata records must have required fields.
        """
        import ingestion.vector_store as vs_module
        import ingestion.embedder as embed_module

        # Redirect vector store to temp dir
        monkeypatch.setattr(vs_module, "FAISS_INDEX_DIR", temp_faiss_dir)

        # Mock embedding API to return deterministic fake vectors
        def fake_get_embeddings(texts):
            return [FAKE_EMBEDDING for _ in texts]

        monkeypatch.setattr(embed_module, "get_embeddings", fake_get_embeddings)

        from ingestion.pipeline import run_ingestion_pipeline

        docx_bytes = _make_dummy_docx(DUMMY_SRS_TEXT)
        result = run_ingestion_pipeline(docx_bytes, "dummy_srs.docx")

        # All returned fields must be present
        assert "chunks_stored" in result
        assert "failed_pages" in result
        assert "document_metadata" in result
        assert "chunk_preview" in result

        # At least 1 chunk stored
        assert result["chunks_stored"] >= 1

        # No failed pages for a clean DOCX
        assert result["failed_pages"] == []

        # Verify metadata in the actual FAISS store
        from ingestion.vector_store import FAISSVectorStore
        store = FAISSVectorStore(index_dir=temp_faiss_dir)
        all_meta = store.get_all_metadata()
        assert len(all_meta) == result["chunks_stored"]

        for record in all_meta:
            assert "Requirement_ID" in record
            assert "chunk_index" in record
            assert "source_document" in record
            assert "text" in record
            assert record["source_document"] == "dummy_srs.docx"

    def test_full_pipeline_pdf(self, temp_faiss_dir, monkeypatch):
        """
        Given a 3-requirement dummy SRS PDF (mocked pdfplumber):
        - Pipeline should extract, chunk, embed, and store.
        """
        import ingestion.vector_store as vs_module
        import ingestion.embedder as embed_module

        monkeypatch.setattr(vs_module, "FAISS_INDEX_DIR", temp_faiss_dir)
        monkeypatch.setattr(embed_module, "get_embeddings", lambda texts: [FAKE_EMBEDDING] * len(texts))

        with patch("pdfplumber.open") as mock_open:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = DUMMY_SRS_TEXT
            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page]
            mock_open.return_value.__enter__.return_value = mock_pdf

            from ingestion.pipeline import run_ingestion_pipeline
            result = run_ingestion_pipeline(b"%PDF-1.4 fake", "test_srs.pdf")

        assert result["chunks_stored"] >= 1
        assert result["document_metadata"]["filename"] == "test_srs.pdf"

    def test_pipeline_chunk_preview(self, temp_faiss_dir, monkeypatch):
        """chunk_preview should contain at most 3 items."""
        import ingestion.vector_store as vs_module
        import ingestion.embedder as embed_module

        monkeypatch.setattr(vs_module, "FAISS_INDEX_DIR", temp_faiss_dir)
        monkeypatch.setattr(embed_module, "get_embeddings", lambda texts: [FAKE_EMBEDDING] * len(texts))

        from ingestion.pipeline import run_ingestion_pipeline
        docx_bytes = _make_dummy_docx(DUMMY_SRS_TEXT)
        result = run_ingestion_pipeline(docx_bytes, "srs.docx")

        assert len(result["chunk_preview"]) <= 3
