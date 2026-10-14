
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import (
    ALLOWED_ORIGINS,
    APP_DESCRIPTION,
    APP_TITLE,
    APP_VERSION,
    SPACY_MODEL_PRIMARY,
    SPACY_MODEL_SECONDARY,
    SENTENCE_TRANSFORMER_MODEL,
)
from backend.api.routes import router


# ============================================================
# LOGGING CONFIGURATION
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    force=True,
)

logger = logging.getLogger("ats_resume_scorer")


# ============================================================
# APPLICATION LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=== LIFESPAN ENTERED ===", flush=True)
    logger.info("Starting ATS Resume Analyzer API")

    # --------------------------------------------------------
    # STEP 1: Import and load spaCy
    # --------------------------------------------------------

    print("=== BEFORE SPACY IMPORT ===", flush=True)

    import spacy

    print("=== SPACY IMPORT COMPLETE ===", flush=True)

    start_time = time.time()

    logger.info("Loading primary spaCy model: %s", SPACY_MODEL_PRIMARY)

    try:
        app.state.nlp = spacy.load(SPACY_MODEL_PRIMARY)

        logger.info(
            "Loaded spaCy model %s in %.2f seconds",
            SPACY_MODEL_PRIMARY,
            time.time() - start_time,
        )

    except OSError:
        logger.warning(
            "Primary spaCy model %s unavailable; trying fallback %s",
            SPACY_MODEL_PRIMARY,
            SPACY_MODEL_SECONDARY,
        )

        start_time = time.time()

        app.state.nlp = spacy.load(SPACY_MODEL_SECONDARY)

        logger.info(
            "Loaded fallback spaCy model %s in %.2f seconds",
            SPACY_MODEL_SECONDARY,
            time.time() - start_time,
        )

    # --------------------------------------------------------
    # STEP 2: Import Sentence Transformers
    # --------------------------------------------------------

    print("=== BEFORE SENTENCE TRANSFORMERS IMPORT ===", flush=True)

    from sentence_transformers import SentenceTransformer

    print("=== SENTENCE TRANSFORMERS IMPORT COMPLETE ===", flush=True)

    # --------------------------------------------------------
    # STEP 3: Load the fine-tuned Hugging Face model
    # --------------------------------------------------------

    hf_token = os.getenv("HF_TOKEN")

    logger.info(
        "Hugging Face token configured: %s",
        bool(hf_token),
    )

    logger.info(
        "Loading SentenceTransformer model: %s",
        SENTENCE_TRANSFORMER_MODEL,
    )

    start_time = time.time()

    app.state.embedder = SentenceTransformer(
        SENTENCE_TRANSFORMER_MODEL,
        token=hf_token or None,
    )

    logger.info(
        "Loaded SentenceTransformer model %s in %.2f seconds",
        SENTENCE_TRANSFORMER_MODEL,
        time.time() - start_time,
    )

    # --------------------------------------------------------
    # STEP 4: Startup complete
    # --------------------------------------------------------

    logger.info("All models loaded successfully")
    print("=== ALL MODELS LOADED; APPLICATION READY ===", flush=True)

    yield

    # --------------------------------------------------------
    # STEP 5: Shutdown
    # --------------------------------------------------------

    logger.info("Shutting down ATS Resume Analyzer API")


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ============================================================
# CORS CONFIGURATION
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROUTES
# ============================================================

app.include_router(router)


@app.get("/")
async def root():
    return {
        "name": "ATS Resume Analyzer API",
        "version": APP_VERSION,
        "endpoints": {
            "POST /api/v1/analyze-resume": "Analyze a resume",
            "GET /api/v1/history": "Get user history",
            "DELETE /api/v1/history/:id": "Delete a history entry",
            "GET /api/v1/health": "Health check",
            "POST /api/v1/generate-pdf": "Generate PDF report from data",
        },
    }


# ============================================================
# LOCAL DEVELOPMENT
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
