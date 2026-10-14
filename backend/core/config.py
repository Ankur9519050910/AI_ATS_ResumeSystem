import os
from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT CONFIGURATION
# ============================================================

# config.py
#   ↓ parents[0] = core/
#   ↓ parents[1] = backend/
#   ↓
# backend/.env

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)


# ============================================================
# API METADATA
# ============================================================

APP_TITLE = "ATS RESUME ANALYZER API"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Analyse resumes against job descriptions using NLP + ML"


# ============================================================
# CORS
# ============================================================

# Development React frontend
# Vite normally runs on 5173.
#
# Add your production React/Vercel URL here later.

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173"

    # Add your deployed React frontend later:
    # "https://your-react-app.vercel.app",
]


# ============================================================
# FILE CONFIGURATION
# ============================================================

MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

SUPPORTED_MIME_TYPES = {
    "application/pdf": "pdf",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
}


# ============================================================
# NLP / ML MODELS
# ============================================================

# SPACY_MODEL_PRIMARY = "en_core_web_md"
# SPACY_MODEL_SECONDARY = "en_core_web_sm"

SPACY_MODEL_PRIMARY = "en_core_web_sm"
SPACY_MODEL_SECONDARY = "en_core_web_sm"

SENTENCE_TRANSFORMER_MODEL = os.getenv(
    "SENTENCE_TRANSFORMER_MODEL",
    "all-MiniLM-L6-v2",
)


# ============================================================
# ATS SCORE WEIGHTS
# ============================================================

SCORE_WEIGHTS = {
    "formatting": 20,
    "keywords": 25,
    "content": 25,
    "skill_validation": 15,
    "ats_compatibility": 15,
}


# ============================================================
# JOB DESCRIPTION MATCHING
# ============================================================

JD_KEYWORD_WEIGHT = 0.6
JD_SEMANTIC_WEIGHT = 0.4


# ============================================================
# SUPABASE
# ============================================================

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")


# ============================================================
# GROQ
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


# ============================================================
# DEBUG / CONFIGURATION CHECK
# ============================================================

print("Environment configuration:")
print("  SUPABASE_URL loaded       :", bool(SUPABASE_URL))
print("  SUPABASE_KEY loaded       :", bool(SUPABASE_KEY))
print("  SUPABASE_ANON_KEY loaded  :", bool(SUPABASE_ANON_KEY))
print("  SUPABASE_JWT_SECRET loaded:", bool(SUPABASE_JWT_SECRET))
print("  GROQ_API_KEY loaded       :", bool(GROQ_API_KEY))
print("  ENV file                  :", ENV_FILE)