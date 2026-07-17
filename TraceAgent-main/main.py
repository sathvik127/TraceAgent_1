import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI

from ingestion.router import router as ingestion_router

# ── Environment & Logging ─────────────────────────────────────────────────────
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="TraceAgent API",
    version="1.0.0",
    description=(
        "Automated SRS-to-Code Traceability & Compliance Auditor. "
        "Sprint 1: Document Ingestion & Semantic Storage pipeline."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(ingestion_router)

# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health_check():
    """Confirm server is running and env variables are configured."""
    has_groq = bool(os.getenv("GROQ_API_KEY"))
    has_openrouter = bool(os.getenv("OPENROUTER_API_KEY"))
    use_local_db = os.getenv("USE_LOCAL_VECTOR_DB", "true").lower() == "true"
    has_pinecone = bool(os.getenv("PINECONE_API_KEY")) and os.getenv("PINECONE_API_KEY") != "your_pinecone_api_key_here"

    return {
        "status": "healthy",
        "message": "TraceAgent API is up and running!",
        "env_check": {
            "groq_configured": has_groq,
            "openrouter_configured": has_openrouter,
            "vector_db_mode": "local_faiss" if use_local_db else "pinecone",
            "pinecone_configured": has_pinecone,
        },
    }
