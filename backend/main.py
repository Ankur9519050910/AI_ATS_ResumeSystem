import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import(
    ALLOWED_ORIGINS, 
    APP_DESCRIPTION, 
    APP_TITLE, 
    APP_VERSION, 
    SPACY_MODEL_PRIMARY, 
    SPACY_MODEL_SECONDARY, SENTENCE_TRANSFORMER_MODEL
)
from backend.api.routes import router

logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger("ats_resume_scorer")


@asynccontextmanager
async def lifespan(app: FastAPI):
    import os
    import time
    import spacy
    from sentence_transformers import SentenceTransformer

    print("=== CUSTOM LIFESPAN STARTED ===", flush=True)
    logger.info("Starting ATS Resume Analyzer API...")

    # Step 1: Load spaCy
    start = time.time()
    logger.info("Loading spaCy model: %s", SPACY_MODEL_PRIMARY)

    try:
        app.state.nlp = spacy.load(SPACY_MODEL_PRIMARY)
        logger.info("Loaded %s in %.1f seconds",
                    SPACY_MODEL_PRIMARY, time.time() - start)
    except OSError:
        logger.warning("Primary spaCy model unavailable; trying %s",
                       SPACY_MODEL_SECONDARY)
        start = time.time()
        app.state.nlp = spacy.load(SPACY_MODEL_SECONDARY)
        logger.info("Loaded fallback model in %.1f seconds",
                    time.time() - start)

    # Step 2: Load Sentence Transformer
    start = time.time()
    hf_token = os.getenv("HF_TOKEN")

    logger.info("Loading SentenceTransformer: %s",
                SENTENCE_TRANSFORMER_MODEL)
    logger.info("HF_TOKEN configured: %s", bool(hf_token))

    app.state.embedder = SentenceTransformer(
        SENTENCE_TRANSFORMER_MODEL,
        token=hf_token or None,
    )

    logger.info("Loaded SentenceTransformer in %.1f seconds",
                time.time() - start)
    logger.info("All models loaded. API is ready.")

    yield

    logger.info("Shutting down the API.")


app=FastAPI(
    title=APP_TITLE, 
    description=APP_DESCRIPTION, 
    version=APP_VERSION, 
    lifespan=lifespan,
    docs_url='/docs',
    redoc_url='/redoc'
)

app.add_middleware(
    CORSMiddleware, 
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True, 
    allow_methods     = ['*'],
    allow_headers     = ['*'],

)

app.include_router(router)

@app.get('/')
async def root():
    return {
        'name':      'ATS Resume Analyzer API',
        'version':   '2.0.0',
        'endpoints': {
            'POST   /api/v1/analyze-resume': 'Analyze a resume',
            'GET    /api/v1/history':        'Get user history',
            'DELETE /api/v1/history/:id':    'Delete a history entry',
            'GET    /api/v1/health':         'Health check',
            'POST   /api/v1/generate-pdf':   'Generate PDF report from data',
        },
    }

if __name__=='__main__':
    import uvicorn
    uvicorn.run(
        'backend.main:app',
        host    = '0.0.0.0',
        port    = 8000,
        reload  = True,    # Auto-restart on code changes (dev only)
    )