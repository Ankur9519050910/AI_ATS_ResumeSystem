
from typing import Dict, List, Optional

import numpy as np
import spacy
from sentence_transformers import SentenceTransformer

from backend.utils.matching import (
    fuzzy_match_keywords,
    normalize_skill,
)


def _normalize(value: str) -> str:
    """Normalize a skill or keyword before comparison."""
    return normalize_skill(value).strip().lower()


def _unique_terms(items: Optional[List[str]]) -> List[str]:
    """Remove duplicates while preserving the first display spelling."""
    unique = []
    seen = set()

    for item in items or []:
        if not isinstance(item, str) or not item.strip():
            continue

        original = item.strip()
        canonical = _normalize(original)

        if not canonical or canonical in seen:
            continue

        seen.add(canonical)
        unique.append(original)

    return unique


def calculate_semantic_similarity(
    resume_text: str,
    jd_text: str,
    embedder: SentenceTransformer,
) -> float:
    """Calculate cosine similarity between a resume and a job description."""
    if not resume_text or not jd_text:
        return 0.0

    try:
        embeddings = np.asarray(
            embedder.encode(
                [resume_text[:5000], jd_text[:5000]],
                convert_to_tensor=False,
                normalize_embeddings=True,
            )
        )

        if embeddings.ndim != 2 or len(embeddings) != 2:
            return 0.0

        similarity = float(np.dot(embeddings[0], embeddings[1]))
        return float(np.clip(similarity, 0.0, 1.0))

    except Exception:
        return 0.0


def identify_matched_keywords(
    resume_keywords: List[str],
    jd_keywords: List[str],
) -> List[str]:
    """Return unique job-description keywords matched in the resume."""
    result = fuzzy_match_keywords(
        resume_keywords or [],
        jd_keywords or [],
        threshold=85,
    )

    return result["matched"]


def identify_missing_keywords(
    resume_keywords: List[str],
    jd_keywords: List[str],
    top_n: int = 15,
) -> List[str]:
    """Return job-description keywords that are not matched."""
    result = fuzzy_match_keywords(
        resume_keywords or [],
        jd_keywords or [],
        threshold=85,
    )

    return result["missing"][:max(0, top_n)]


def analyze_skills_gap(
    resume_skills: List[str],
    jd_text: str,
    nlp: spacy.Language,
    jd_skills: Optional[List[str]] = None,
) -> List[str]:
    """Identify job-related skills missing from the resume."""

    candidates = _unique_terms(jd_skills)

    # Fallback when structured job-description skills are unavailable.
    if not candidates and jd_text:
        doc = nlp(jd_text[:5000])

        extracted = [
            entity.text.strip()
            for entity in doc.ents
            if entity.label_ in {"PRODUCT", "LANGUAGE"}
            and entity.text.strip()
        ]

        candidates = _unique_terms(extracted)

    resume_skills = _unique_terms(resume_skills)

    if not candidates:
        return []

    result = fuzzy_match_keywords(
        resume_keywords=resume_skills,
        jd_keywords=candidates,
        threshold=85,
    )

    return result["missing"][:20]


def calculate_match_percentage(
    resume_keywords: List[str],
    jd_keywords: List[str],
    semantic_similarity: float,
) -> float:
    """Combine keyword overlap (60%) and semantic similarity (40%)."""

    unique_jd_keywords = _unique_terms(jd_keywords)

    if not unique_jd_keywords:
        return 0.0

    result = fuzzy_match_keywords(
        resume_keywords=resume_keywords or [],
        jd_keywords=unique_jd_keywords,
        threshold=85,
    )

    keyword_overlap = (
        len(result["matched"]) / len(unique_jd_keywords)
    )

    semantic_similarity = float(
        np.clip(semantic_similarity, 0.0, 1.0)
    )

    match_percentage = (
        keyword_overlap * 0.60
        + semantic_similarity * 0.40
    ) * 100.0

    return round(
        float(np.clip(match_percentage, 0.0, 100.0)),
        1,
    )


def compare_resume_with_jd(
    resume_text: str,
    resume_keywords: List[str],
    resume_skills: List[str],
    jd_text: str,
    jd_keywords: List[str],
    embedder: SentenceTransformer,
    nlp: spacy.Language,
    jd_skills: Optional[List[str]] = None,
) -> Dict:
    """Compare a resume with a job description."""

    resume_keywords = resume_keywords or []
    resume_skills = resume_skills or []
    jd_keywords = _unique_terms(jd_keywords)
    jd_skills = _unique_terms(jd_skills)

    # Include both extracted resume keywords and listed skills.
    resume_terms = _unique_terms(resume_keywords + resume_skills)

    semantic_similarity = calculate_semantic_similarity(
        resume_text=resume_text,
        jd_text=jd_text,
        embedder=embedder,
    )

    keyword_result = fuzzy_match_keywords(
        resume_keywords=resume_terms,
        jd_keywords=jd_keywords,
        threshold=85,
    )

    matched_keywords = keyword_result["matched"]
    missing_keywords = keyword_result["missing"]

    # Use structured JD skills for the skill gap.
    # Do not treat every general keyword as a technical skill.
    skills_gap = analyze_skills_gap(
        resume_skills=resume_skills,
        jd_text=jd_text,
        nlp=nlp,
        jd_skills=jd_skills,
    )

    match_percentage = calculate_match_percentage(
        resume_keywords=resume_terms,
        jd_keywords=jd_keywords,
        semantic_similarity=semantic_similarity,
    )

    return {
        "match_percentage": match_percentage,
        "semantic_similarity": round(semantic_similarity, 3),
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "skills_gap": skills_gap,
    }
