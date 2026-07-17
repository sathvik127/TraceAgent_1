"""
TRACE-101: Unit Tests — Document Extractor
==========================================
Tests covering the acceptance criteria from the sprint plan:
  1. Valid PDF upload → extracts text successfully
  2. Valid DOCX upload → extracts text successfully
  3. Unsupported file type → raises ValueError (mapped to HTTP 415)
  4. PDF with one blank page → appears in failed_pages with reason

Run with:
    pytest ingestion/tests/test_extractor.py -v
"""

import io
import textwrap
from unittest.mock import MagicMock, patch

import pytest

from ingestion.extractor import (
    SUPPORTED_EXTENSIONS,
    extract_document,
    extract_pdf,
    extract_docx,
    sanitize_text,
)


# ─────────────────────────────────────────────
# Fixtures — synthetic file bytes
# ─────────────────────────────────────────────

def _make_minimal_pdf(page_texts: list[str]) -> bytes:
    """
    Build a minimal but valid PDF in pure bytes.
    Uses pdfplumber-compatible structure (real PDF objects).
    We mock pdfplumber instead of building a real PDF to keep tests dependency-free.
    """
    # This is a placeholder; actual bytes are provided via the mock below.
    return b"%PDF-1.4 placeholder"


def _make_minimal_docx(paragraphs: list[str]) -> bytes:
    """Create an actual in-memory DOCX using python-docx."""
    from docx import Document as DocxDocument
    doc = DocxDocument()
    for para in paragraphs:
        doc.add_paragraph(para)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


# ─────────────────────────────────────────────
# 1. Sanitize Text
# ─────────────────────────────────────────────

class TestSanitizeText:
    def test_strips_standalone_page_numbers(self):
        raw = "Introduction\n\n3\n\nThis is some content."
        cleaned = sanitize_text(raw)
        assert "\n3\n" not in cleaned
        assert "Introduction" in cleaned
        assert "This is some content." in cleaned

    def test_strips_toc_lines(self):
        raw = "Requirements\n\n1.1 Overview ............ 4\n\nActual content here."
        cleaned = sanitize_text(raw)
        assert "..........." not in cleaned
        assert "Actual content here." in cleaned

    def test_strips_toc_heading(self):
        raw = "Table of Contents\n\n1.1 Overview ........... 3\n\nBody text."
        cleaned = sanitize_text(raw)
        assert "Table of Contents" not in cleaned

    def test_preserves_regular_paragraphs(self):
        raw = "FR-01: The system shall authenticate users via username and password."
        cleaned = sanitize_text(raw)
        assert cleaned == raw.strip()

    def test_empty_string_returns_empty(self):
        assert sanitize_text("") == ""


# ─────────────────────────────────────────────
# 2. PDF Extraction (mocked pdfplumber)
# ─────────────────────────────────────────────

class TestExtractPdf:
    def _mock_page(self, text: str | None):
        """Create a mock pdfplumber page with given extract_text() return value."""
        page = MagicMock()
        page.extract_text.return_value = text
        return page

    def test_single_good_page(self):
        """A PDF with one normal page should extract text and have no failed pages."""
        content = "FR-01: The system shall provide user registration functionality."
        fake_pages = [self._mock_page(content)]

        with patch("pdfplumber.open") as mock_open:
            mock_pdf = MagicMock()
            mock_pdf.pages = fake_pages
            mock_open.return_value.__enter__.return_value = mock_pdf

            result = extract_pdf(b"%PDF-1.4 fake")

        assert len(result["failed_pages"]) == 0
        assert "FR-01" in result["extracted_text"]
        assert result["page_count"] == 1

    def test_blank_page_logged_in_failed_pages(self):
        """A blank page should appear in failed_pages with a descriptive reason."""
        content = "FR-01: System shall support login."
        fake_pages = [
            self._mock_page(content),
            self._mock_page(""),          # blank page
            self._mock_page(content),
        ]

        with patch("pdfplumber.open") as mock_open:
            mock_pdf = MagicMock()
            mock_pdf.pages = fake_pages
            mock_open.return_value.__enter__.return_value = mock_pdf

            result = extract_pdf(b"%PDF-1.4 fake")

        assert len(result["failed_pages"]) == 1
        failed = result["failed_pages"][0]
        assert failed["page_number"] == 2
        assert "blank" in failed["reason"] or "threshold" in failed["reason"]

    def test_scanned_page_returns_none(self):
        """A page returning None (scanned image) should appear in failed_pages."""
        fake_pages = [self._mock_page(None)]

        with patch("pdfplumber.open") as mock_open:
            mock_pdf = MagicMock()
            mock_pdf.pages = fake_pages
            mock_open.return_value.__enter__.return_value = mock_pdf

            result = extract_pdf(b"%PDF-1.4 fake")

        assert len(result["failed_pages"]) == 1
        assert "scanned" in result["failed_pages"][0]["reason"]

    def test_multi_page_partial_failure(self):
        """3 pages, 1 blank → 2 extracted, 1 in failed_pages."""
        fake_pages = [
            self._mock_page("FR-01: Registration process allows users to sign up."),
            self._mock_page(""),
            self._mock_page("FR-02: Login process requires a valid username and password."),
        ]

        with patch("pdfplumber.open") as mock_open:
            mock_pdf = MagicMock()
            mock_pdf.pages = fake_pages
            mock_open.return_value.__enter__.return_value = mock_pdf

            result = extract_pdf(b"%PDF-1.4 fake")

        assert result["page_count"] == 3
        assert len(result["failed_pages"]) == 1
        assert "FR-01" in result["extracted_text"]
        assert "FR-02" in result["extracted_text"]


# ─────────────────────────────────────────────
# 3. DOCX Extraction
# ─────────────────────────────────────────────

class TestExtractDocx:
    def test_extracts_paragraphs(self):
        """A DOCX with several paragraphs should be fully extracted."""
        paragraphs = [
            "FR-01: The system shall support user registration.",
            "FR-02: The system shall support user login.",
            "FR-03: The system shall display account balance.",
        ]
        docx_bytes = _make_minimal_docx(paragraphs)
        result = extract_docx(docx_bytes)

        assert "FR-01" in result["extracted_text"]
        assert "FR-02" in result["extracted_text"]
        assert "FR-03" in result["extracted_text"]
        assert result["failed_pages"] == []
        assert result["page_count"] is None  # DOCX has no reliable page count

    def test_empty_paragraphs_are_skipped(self):
        """Empty paragraphs should not appear in extracted text."""
        paragraphs = ["FR-01: Registration.", "", "  ", "FR-02: Login."]
        docx_bytes = _make_minimal_docx(paragraphs)
        result = extract_docx(docx_bytes)

        # Should not have double-blank-line artifacts from empty paras
        assert "FR-01" in result["extracted_text"]
        assert "FR-02" in result["extracted_text"]


# ─────────────────────────────────────────────
# 4. Dispatcher — extract_document
# ─────────────────────────────────────────────

class TestExtractDocument:
    def test_unsupported_extension_raises_value_error(self):
        """Unsupported file types must raise ValueError (→ HTTP 415 in router)."""
        with pytest.raises(ValueError, match="Unsupported file type"):
            extract_document(b"fake content", "document.txt")

    def test_no_extension_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported file type"):
            extract_document(b"fake content", "document")

    def test_docx_dispatched_correctly(self):
        """A .docx filename should be routed to the DOCX extractor."""
        paragraphs = ["FR-01: Registration.", "FR-02: Login."]
        docx_bytes = _make_minimal_docx(paragraphs)

        result = extract_document(docx_bytes, "srs_document.docx")

        assert "FR-01" in result["extracted_text"]
        assert "document_metadata" in result
        assert result["document_metadata"]["filename"] == "srs_document.docx"
        assert "failed_pages" in result

    def test_pdf_dispatched_correctly(self):
        """A .pdf filename should be routed to the PDF extractor."""
        content = "FR-01: System shall register users."

        with patch("pdfplumber.open") as mock_open:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = content
            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page]
            mock_open.return_value.__enter__.return_value = mock_pdf

            result = extract_document(b"%PDF-1.4 fake", "srs.pdf")

        assert "FR-01" in result["extracted_text"]
        assert result["document_metadata"]["filename"] == "srs.pdf"

    def test_metadata_fields_present(self):
        """document_metadata must contain: filename, upload_date, page_count, version."""
        paragraphs = ["FR-01: Registration."]
        docx_bytes = _make_minimal_docx(paragraphs)
        result = extract_document(docx_bytes, "srs.docx")

        meta = result["document_metadata"]
        assert "filename" in meta
        assert "upload_date" in meta
        assert "page_count" in meta
        assert "version" in meta

    def test_supported_extensions_set(self):
        """Verify the supported extensions constant."""
        assert ".pdf" in SUPPORTED_EXTENSIONS
        assert ".docx" in SUPPORTED_EXTENSIONS
        assert ".txt" not in SUPPORTED_EXTENSIONS
