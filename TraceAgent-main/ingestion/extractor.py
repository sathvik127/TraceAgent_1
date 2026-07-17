"""
TRACE-101: Document Extractor & Sanitizer
==========================================
Handles PDF and DOCX text extraction from SRS documents.
- PDF: pdfplumber (per-page extraction with failure logging)
- DOCX: python-docx (paragraph-level extraction)
- Sanitization: strips page numbers, repeated headers/footers, ToC patterns
"""

import io
import re
import logging
from datetime import datetime, timezone
from typing import Any

import pdfplumber
from docx import Document

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Sanitization helpers
# ─────────────────────────────────────────────

# Patterns for content we want to strip
_PAGE_NUMBER_RE = re.compile(r"^\s*\d+\s*$", re.MULTILINE)          # e.g. standalone "3"
_TOC_LINE_RE = re.compile(r"^.+\.{4,}\s*\d+\s*$", re.MULTILINE)    # "Section ........ 12"
_TOC_HEADING_RE = re.compile(
    r"^(table\s+of\s+contents|contents)\s*$", re.IGNORECASE | re.MULTILINE
)

# Minimum character threshold per page; below this we consider it a failure  
_MIN_PAGE_CHARS = 20


def sanitize_text(raw_text: str) -> str:
    """
    Strip noise from extracted SRS text:
      - Standalone page-number lines  (e.g. "  3  ")
      - Table-of-Contents lines        (e.g. "1.2 Overview ........ 4")
      - 'Table of Contents' headings
    Returns cleaned, whitespace-normalised text.
    """
    text = _TOC_HEADING_RE.sub("", raw_text)
    text = _TOC_LINE_RE.sub("", text)
    text = _PAGE_NUMBER_RE.sub("", text)
    # Collapse runs of blank lines to a single blank line
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _detect_failure_reason(page_text: str | None) -> str:
    """Infer why a page yielded no usable text."""
    if page_text is None:
        return "scanned_image_or_no_text_layer"
    if len(page_text.strip()) == 0:
        return "blank_page"
    return "below_minimum_character_threshold"


# ─────────────────────────────────────────────
# PDF Extraction
# ─────────────────────────────────────────────

def extract_pdf(file_bytes: bytes) -> dict[str, Any]:
    """
    Extract text from a PDF SRS document using pdfplumber.

    Returns:
        {
            "extracted_text": str,
            "failed_pages": [{"page_number": int, "reason": str}],
            "page_count": int,
        }
    """
    extracted_pages: list[str] = []
    failed_pages: list[dict[str, Any]] = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        page_count = len(pdf.pages)
        for i, page in enumerate(pdf.pages, start=1):
            try:
                raw = page.extract_text()
                if raw is None or len(raw.strip()) < _MIN_PAGE_CHARS:
                    reason = _detect_failure_reason(raw)
                    failed_pages.append({"page_number": i, "reason": reason})
                    logger.warning("PDF page %d failed extraction: %s", i, reason)
                else:
                    extracted_pages.append(raw)
            except Exception as exc:  # noqa: BLE001
                reason = f"extraction_error: {type(exc).__name__}"
                failed_pages.append({"page_number": i, "reason": reason})
                logger.error("PDF page %d raised exception: %s", i, exc)

    raw_combined = "\n\n".join(extracted_pages)
    return {
        "extracted_text": sanitize_text(raw_combined),
        "failed_pages": failed_pages,
        "page_count": page_count,
    }


# ─────────────────────────────────────────────
# DOCX Extraction
# ─────────────────────────────────────────────

def extract_docx(file_bytes: bytes) -> dict[str, Any]:
    """
    Extract text from a DOCX SRS document using python-docx.

    DOCX files don't have discrete 'pages' in a reliable way,
    so we treat each paragraph as a unit.

    Returns:
        {
            "extracted_text": str,
            "failed_pages": [],     # always empty for DOCX
            "page_count": None,     # not available in DOCX
        }
    """
    doc = Document(io.BytesIO(file_bytes))
    paragraphs: list[str] = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)

    raw_combined = "\n\n".join(paragraphs)
    return {
        "extracted_text": sanitize_text(raw_combined),
        "failed_pages": [],
        "page_count": None,  # DOCX does not expose reliable page count
    }


# ─────────────────────────────────────────────
# Metadata Builder
# ─────────────────────────────────────────────

def build_document_metadata(
    filename: str,
    page_count: int | None,
    upload_date: str | None = None,
) -> dict[str, Any]:
    """Build the document_metadata block for the API response."""
    return {
        "filename": filename,
        "upload_date": upload_date or datetime.now(timezone.utc).isoformat(),
        "page_count": page_count,
        "version": "1.0",
    }


# ─────────────────────────────────────────────
# Public dispatcher
# ─────────────────────────────────────────────

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def extract_document(file_bytes: bytes, filename: str) -> dict[str, Any]:
    """
    Top-level dispatcher. Chooses PDF or DOCX extractor based on filename.

    Returns:
        {
            "extracted_text": str,
            "document_metadata": dict,
            "failed_pages": list,
        }

    Raises:
        ValueError: if the file extension is not supported.
    """
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == ".pdf":
        result = extract_pdf(file_bytes)
    elif ext == ".docx":
        result = extract_docx(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: '{ext}'. Only .pdf and .docx are accepted.")

    metadata = build_document_metadata(
        filename=filename,
        page_count=result["page_count"],
    )

    return {
        "extracted_text": result["extracted_text"],
        "document_metadata": metadata,
        "failed_pages": result["failed_pages"],
    }
