"""
TRACE-101 / TRACE-102: Ingestion API Router
=============================================
Mounts at: /api/v1/documents

Endpoints:
  POST /upload   — Extract & sanitize a PDF/DOCX file (TRACE-101)
  POST /process  — Full pipeline: extract → chunk → embed → store (TRACE-102)
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, File, status
from fastapi.responses import JSONResponse

from .extractor import extract_document, SUPPORTED_EXTENSIONS
from .pipeline import run_ingestion_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/documents",
    tags=["Document Ingestion"],
)

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _get_extension(filename: str) -> str:
    """Return lowercase file extension including dot, e.g. '.pdf'."""
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()


def _validate_file_type(filename: str) -> None:
    """
    Raise HTTP 415 if the uploaded file is not .pdf or .docx.
    """
    ext = _get_extension(filename)
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type '{ext}'. "
                f"Only {', '.join(sorted(SUPPORTED_EXTENSIONS))} files are accepted."
            ),
        )


# ─────────────────────────────────────────────
# POST /api/v1/documents/upload   (TRACE-101)
# ─────────────────────────────────────────────

@router.post(
    "/upload",
    summary="Upload and extract SRS document",
    status_code=status.HTTP_200_OK,
    response_description=(
        "Extracted text, document metadata, and list of failed pages"
    ),
)
async def upload_document(
    file: UploadFile = File(..., description="SRS document (.pdf or .docx)"),
) -> JSONResponse:
    """
    **TRACE-101** — Upload a PDF or DOCX SRS document.

    - Validates file type (HTTP 415 for unsupported types)
    - Extracts ≥95% of body text; logs failed pages
    - Returns structured JSON with `extracted_text`, `document_metadata`, `failed_pages`
    """
    _validate_file_type(file.filename or "")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        result: dict[str, Any] = extract_document(file_bytes, file.filename or "upload")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error during document extraction")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraction failed: {type(exc).__name__}: {exc}",
        ) from exc

    logger.info(
        "Uploaded '%s' — %d chars extracted, %d pages failed",
        file.filename,
        len(result["extracted_text"]),
        len(result["failed_pages"]),
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "success",
            "extracted_text": result["extracted_text"],
            "document_metadata": result["document_metadata"],
            "failed_pages": result["failed_pages"],
        },
    )


# ─────────────────────────────────────────────
# POST /api/v1/documents/process  (TRACE-102)
# ─────────────────────────────────────────────

@router.post(
    "/process",
    summary="Full ingestion pipeline: extract → chunk → embed → store",
    status_code=status.HTTP_200_OK,
    response_description=(
        "Number of chunks stored, failed pages, document metadata, and preview chunks"
    ),
)
async def process_document(
    file: UploadFile = File(..., description="SRS document (.pdf or .docx)"),
) -> JSONResponse:
    """
    **TRACE-102** — Full SRS ingestion pipeline.

    Runs the complete pipeline on an uploaded document:
    1. Extract & sanitize text (pdfplumber / python-docx)
    2. Chunk text (LangChain RecursiveCharacterTextSplitter)
    3. Embed chunks (BGE-M3 via OpenRouter, with retry backoff)
    4. Upsert embeddings into vector store (FAISS or Pinecone)

    Returns chunk count, metadata, failed pages, and a 3-chunk preview.
    """
    _validate_file_type(file.filename or "")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        result: dict[str, Any] = run_ingestion_pipeline(file_bytes, file.filename or "upload")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Pipeline error during document processing")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline failed: {type(exc).__name__}: {exc}",
        ) from exc

    logger.info(
        "Processed '%s' — %d chunks stored",
        file.filename,
        result["chunks_stored"],
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "success",
            "chunks_stored": result["chunks_stored"],
            "failed_pages": result["failed_pages"],
            "document_metadata": result["document_metadata"],
            "chunk_preview": result["chunk_preview"],
        },
    )
