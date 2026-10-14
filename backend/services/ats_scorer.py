
import re
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import spacy
from sentence_transformers import SentenceTransformer

from backend.core.config import SENTENCE_TRANSFORMER_MODEL
from backend.utils.file_utils import log_warning
from backend.utils.matching import fuzzy_match_keywords, normalize_skill


ZIP_CODE_PATTERN = r"\b\d{5}(?:-\d{4})?\b"

STREET_ADDRESS_PATTERN = (
    r"\b\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+"
    r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|"
    r"Lane|Ln|Drive|Dr|Court|Ct|Circle|Cir|Way|Place|Pl)\b"
)


def _safe_text(value: Any) -> str:
    """Convert optional values to safe strings."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return " ".join(_safe_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_safe_text(item) for item in value.values())
    return ""


def _tier_score(n: float, tiers: list) -> float:
    """Return points for the highest satisfied threshold."""
    for threshold, points in tiers:
        if n >= threshold:
            return float(points)
    return 0.0


# -------------------------------------------------------------------
# 1. LOCATION AND PRIVACY DETECTION
# -------------------------------------------------------------------

def detect_location_info(text: str, nlp: spacy.Language) -> Dict:
    locations = []

    doc = nlp(text or "")

    for ent in doc.ents:
        if ent.label_ in ("GPE", "LOC"):
            locations.append({
                "text": ent.text,
                "type": ent.label_.lower(),
                "start": ent.start_char,
            })

    for match in re.finditer(
        STREET_ADDRESS_PATTERN, text or "", re.IGNORECASE
    ):
        locations.append({
            "text": match.group(),
            "type": "address",
            "start": match.start(),
        })

    for match in re.finditer(ZIP_CODE_PATTERN, text or ""):
        locations.append({
            "text": match.group(),
            "type": "zip",
            "start": match.start(),
        })

    # Remove duplicate detections.
    unique_locations = []
    seen = set()

    for location in locations:
        key = (
            location["text"].strip().lower(),
            location["type"],
            location["start"],
        )
        if key not in seen:
            seen.add(key)
            unique_locations.append(location)

    locations = unique_locations

    has_address = any(item["type"] == "address" for item in locations)
    has_zip = any(item["type"] == "zip" for item in locations)

    if has_address and has_zip:
        privacy_risk, penalty = "high", 5.0
    elif has_address or has_zip:
        privacy_risk, penalty = "high", 4.0
    elif len(locations) > 3:
        privacy_risk, penalty = "medium", 3.0
    elif locations:
        privacy_risk, penalty = "low", 2.0
    else:
        privacy_risk, penalty = "none", 0.0

    recommendations = []

    if not locations:
        recommendations.append("No privacy concerns detected.")

    if has_address:
        recommendations.append(
            "Remove full street addresses. A resume generally does not "
            "need this level of location detail."
        )

    if has_zip:
        recommendations.append(
            "Remove postal or ZIP codes if they are not necessary."
        )

    if (
        privacy_risk in ("low", "medium")
        and not has_address
        and not has_zip
    ):
        recommendations.append(
            "Consider keeping only your city and state in the contact section."
        )

    return {
        "location_found": bool(locations),
        "detected_locations": locations,
        "privacy_risk": privacy_risk,
        "recommendations": recommendations,
        "penalty_applied": penalty,
    }


# -------------------------------------------------------------------
# 2. SEMANTIC SIMILARITY
# -------------------------------------------------------------------

def _calculate_semantic_similarity(
    skill: str,
    text: str,
    embedder: SentenceTransformer,
) -> float:
    """Calculate cosine similarity between a skill and evidence text."""
    if not skill or not text:
        return 0.0

    try:
        vectors = embedder.encode(
            [skill, text[:5000]],
            convert_to_tensor=False,
            normalize_embeddings=True,
        )

        similarity = float(np.dot(vectors[0], vectors[1]))
        return max(0.0, min(1.0, similarity))

    except Exception as exc:
        log_warning(
            f"Similarity error for '{skill}': {exc}",
            context="ats_scorer",
        )
        return 0.0


def _contains_skill(skill: str, text: str) -> bool:
    """
    Match complete skill names instead of arbitrary substrings.

    Examples:
    - C must not match 'competitive'.
    - JavaScript should match 'JavaScript'.
    - C++ should match 'C++'.
    """
    if not skill or not text:
        return False

    candidate = normalize_skill(skill) or skill
    candidate = candidate.strip()

    if not candidate:
        return False

    # C, C++, and C# require special handling.
    if candidate.lower() == "c":
        pattern = r"(?<![\w+#])c(?![\w+#])"
    elif candidate.lower() == "c++":
        pattern = r"(?<![\w+#])c\+\+(?![\w+#])"
    elif candidate.lower() == "c#":
        pattern = r"(?<![\w+#])c#(?![\w+#])"
    else:
        # Match complete phrases, not substrings inside other words.
        escaped = re.escape(candidate)
        pattern = r"(?<!\w)" + escaped + r"(?!\w)"

    return re.search(pattern, text, re.IGNORECASE) is not None


def _skill_matches(
    skill: str,
    text: str,
    embedder: SentenceTransformer,
    threshold: float = 0.72,
) -> Tuple[bool, float]:
    """Check whether a skill has evidence in a project or experience."""
    if not skill or not text:
        return False, 0.0

    # Exact match is the strongest evidence.
    if _contains_skill(skill, text):
        return True, 1.0

    normalized_skill = normalize_skill(skill) or skill.strip()

    # Semantic matching for very short names causes false positives.
    # Require explicit evidence for short skill names.
    if len(normalized_skill) < 4:
        return False, 0.0

    similarity = _calculate_semantic_similarity(
        normalized_skill,
        text,
        embedder,
    )

    return similarity >= threshold, similarity


# -------------------------------------------------------------------
# 3. SKILL VALIDATION USING PROJECTS AND EXPERIENCE
# -------------------------------------------------------------------

def validate_skills_with_projects(
    skills: List[str],
    projects: List[Dict],
    experience_entries: List[Dict],
    embedder: SentenceTransformer,
    threshold: float = 0.72,
) -> Dict:
    """
    Validate resume skills using project descriptions, project technologies,
    and experience descriptions.

    Expected project format:
    {
        "title": "My Project",
        "description": "Project description",
        "technologies": ["Python", "React", "Node.js"]
    }
    """
    skills = skills or []
    projects = projects or []
    experience_entries = experience_entries or []

    if not skills:
        return {
            "validated_skills": [],
            "unvalidated_skills": [],
            "validation_percentage": 0.0,
            "skill_project_mapping": {},
            "validation_score": 0.0,
        }

    # Build experience evidence.
    experience_texts = []

    for entry in experience_entries:
        if not isinstance(entry, dict):
            continue

        experience_texts.append(
            " ".join([
                _safe_text(entry.get("job_title")),
                _safe_text(entry.get("company")),
                _safe_text(entry.get("description")),
                _safe_text(entry.get("responsibilities")),
                _safe_text(entry.get("achievements")),
                _safe_text(entry.get("technologies")),
                _safe_text(entry.get("skills")),
            ])
        )

    experience_text = " ".join(experience_texts).strip()

    validated_skills = []
    unvalidated_skills = []
    skill_project_mapping = {}

    # Avoid counting the same canonical skill more than once.
    seen_skills = set()

    for skill in skills:
        if not isinstance(skill, str) or not skill.strip():
            continue

        canonical_skill = (normalize_skill(skill) or skill).strip().lower()

        if canonical_skill in seen_skills:
            continue

        seen_skills.add(canonical_skill)

        matching_projects = []
        max_similarity = 0.0

        for project in projects:
            if not isinstance(project, dict):
                continue

            project_title = (
                _safe_text(project.get("title")) or "Untitled Project"
            )

            # Important: technologies are now included as evidence.
            technologies = project.get("technologies", [])

            if isinstance(technologies, str):
                technologies = [
                    item.strip()
                    for item in re.split(r"[,;|]", technologies)
                    if item.strip()
                ]

            if not isinstance(technologies, list):
                technologies = []

            technology_names = [
                _safe_text(item).strip()
                for item in technologies
                if _safe_text(item).strip()
            ]

            project_text = " ".join([
                project_title,
                _safe_text(project.get("description")),
                _safe_text(project.get("details")),
                _safe_text(project.get("features")),
                _safe_text(project.get("responsibilities")),
                " ".join(technology_names),
            ]).strip()

            # Explicit technology-list matches are direct evidence.
            explicit_technology_match = any(
                (normalize_skill(technology) or technology).strip().lower()
                == canonical_skill
                for technology in technology_names
            )

            if explicit_technology_match:
                matched, similarity = True, 1.0
            else:
                matched, similarity = _skill_matches(
                    skill,
                    project_text,
                    embedder,
                    threshold,
                )

            max_similarity = max(max_similarity, similarity)

            if matched and project_title not in matching_projects:
                matching_projects.append(project_title)

        # Check professional experience as separate evidence.
        if experience_text:
            matched, similarity = _skill_matches(
                skill,
                experience_text,
                embedder,
                threshold,
            )

            max_similarity = max(max_similarity, similarity)

            if matched and "Experience Section" not in matching_projects:
                matching_projects.append("Experience Section")

        if matching_projects:
            validated_skills.append({
                "skill": skill,
                "projects": matching_projects,
                "similarity": round(max_similarity, 3),
            })
            skill_project_mapping[skill] = matching_projects
        else:
            unvalidated_skills.append(skill)
            skill_project_mapping[skill] = []

    total_skills = len(validated_skills) + len(unvalidated_skills)

    validation_percentage = (
        len(validated_skills) / total_skills if total_skills else 0.0
    )

    return {
        "validated_skills": validated_skills,
        "unvalidated_skills": unvalidated_skills,
        "validation_percentage": round(validation_percentage, 4),
        "skill_project_mapping": skill_project_mapping,
        "validation_score": round(validation_percentage * 15.0, 2),
    }


# -------------------------------------------------------------------
# 4. FORMATTING SCORE (MAXIMUM 20)
# -------------------------------------------------------------------

def _calc_formatting_score(parsed_resume: Dict, text: str) -> float:
    score = 0.0

    experience = [
        item for item in parsed_resume.get("experience", [])
        if isinstance(item, dict)
    ]
    education = [
        item for item in parsed_resume.get("education", [])
        if isinstance(item, dict)
    ]
    skills = parsed_resume.get("skills", []) or []
    summary = _safe_text(parsed_resume.get("professional_summary"))
    projects = [
        item for item in parsed_resume.get("projects", [])
        if isinstance(item, dict)
    ]

    if experience and any(
        item.get("job_title") or item.get("description")
        for item in experience
    ):
        score += 3.0

    if education:
        score += 2.0

    if len(skills) >= 3:
        score += 2.0

    if len(summary) > 30:
        score += 1.5

    if projects:
        score += 1.5

    bullet_count = sum(
        1
        for line in (text or "").splitlines()
        if re.match(r"^\s*(?:[•\-*◦]|\d+\.)\s+", line)
    )

    score += _tier_score(
        bullet_count,
        [(15, 5.0), (10, 4.0), (5, 3.0), (3, 2.0), (1, 1.0)],
    )

    filled_sections = sum([
        bool(experience),
        bool(education),
        bool(skills),
        bool(summary.strip()),
        bool(projects),
    ])

    score += _tier_score(
        filled_sections,
        [(4, 5.0), (3, 4.0), (2, 3.0), (1, 2.0)],
    )

    return round(min(20.0, max(0.0, score)), 2)


# -------------------------------------------------------------------
# 5. KEYWORD SCORE (MAXIMUM 25)
# -------------------------------------------------------------------

def _calc_keywords_score(
    resume_keywords: List[str],
    skills: List[str],
    jd_keywords: Optional[List[str]] = None,
) -> float:
    score = 0.0

    resume_keywords = resume_keywords or []
    skills = skills or []

    score += _tier_score(
        len(resume_keywords),
        [(20, 10.0), (15, 8.0), (10, 6.0), (5, 4.0), (3, 2.0)],
    )

    score += _tier_score(
        len(skills),
        [(15, 10.0), (10, 8.0), (7, 6.0), (5, 4.0), (3, 2.0)],
    )

    if jd_keywords:
        resume_terms = list(dict.fromkeys(resume_keywords + skills))

        fuzzy_result = fuzzy_match_keywords(
            resume_terms,
            jd_keywords,
            threshold=80,
        )

        matched_count = len(fuzzy_result.get("matched", []))
        match_percentage = min(
            1.0,
            matched_count / len(jd_keywords),
        ) if jd_keywords else 0.0

        score += _tier_score(
            match_percentage,
            [(0.7, 5.0), (0.5, 4.0), (0.3, 3.0), (0.2, 2.0), (0.1, 1.0)],
        )

    elif len(resume_keywords) >= 10:
        score += 3.0

    return round(min(25.0, max(0.0, score)), 2)


# -------------------------------------------------------------------
# 6. CONTENT QUALITY SCORE (MAXIMUM 25)
# -------------------------------------------------------------------

def _calc_content_score(
    text: str,
    action_verbs: List[str],
    grammar_results: Dict,
) -> float:
    score = 0.0
    text = text or ""
    action_verbs = action_verbs or []
    grammar_results = grammar_results or {}

    score += _tier_score(
        len(action_verbs),
        [(15, 10.0), (10, 8.0), (7, 6.0), (5, 4.0), (3, 2.0)],
    )

    number_patterns = [
        r"\d+%",
        r"\$\d+",
        r"\d+[kKmMbB]\b",
        r"\d+\s*(?:users|customers|clients|projects|hours|days|months|years)\b",
        r"(?:increased|decreased|improved|reduced|grew|saved)\s+(?:by\s+)?\d+",
    ]

    achievement_count = sum(
        len(re.findall(pattern, text, re.IGNORECASE))
        for pattern in number_patterns
    )

    score += _tier_score(
        achievement_count,
        [(10, 5.0), (7, 4.0), (5, 3.0), (3, 2.0), (1, 1.0)],
    )

    grammar_penalty = float(grammar_results.get("penalty_applied", 0.0) or 0.0)
    score += max(0.0, 10.0 - grammar_penalty / 2.0)

    return round(min(25.0, max(0.0, score)), 2)


# -------------------------------------------------------------------
# 7. SKILL VALIDATION SCORE (MAXIMUM 15)
# -------------------------------------------------------------------

def _calc_skill_validation_score(validation_results: Dict) -> float:
    validation_results = validation_results or {}

    return round(
        min(
            15.0,
            max(0.0, float(validation_results.get("validation_score", 0.0))),
        ),
        2,
    )


# -------------------------------------------------------------------
# 8. ATS COMPATIBILITY SCORE (MAXIMUM 15)
# -------------------------------------------------------------------

def _calc_ats_compatibility_score(
    text: str,
    location_results: Dict,
    parsed_resume: Dict,
) -> float:
    score = 15.0
    location_results = location_results or {}
    parsed_resume = parsed_resume or {}
    text = text or ""

    score -= float(location_results.get("penalty_applied", 0.0) or 0.0)

    special_chars = len(re.findall(r"[│┤├┼┴┬╔╗╚╝═║╠╣╦╩╬]", text))

    if special_chars > 20:
        score -= 2.0
    elif special_chars > 10:
        score -= 1.0

    experience = [
        item for item in parsed_resume.get("experience", [])
        if isinstance(item, dict)
    ]
    education = [
        item for item in parsed_resume.get("education", [])
        if isinstance(item, dict)
    ]
    skills = parsed_resume.get("skills", []) or []

    experience_description_length = sum(
        len(_safe_text(item.get("description")))
        for item in experience
    )

    education_description_length = sum(
        len(_safe_text(item.get("degree")))
        + len(_safe_text(item.get("institution")))
        for item in education
    )

    short_sections = sum([
        bool(experience) and experience_description_length < 20,
        bool(education) and education_description_length < 20,
        bool(skills) and len(skills) < 2,
    ])

    if short_sections >= 2:
        score -= 2.0
    elif short_sections == 1:
        score -= 1.0

    if experience and len(skills) > 5:
        score += 1.0

    return round(min(15.0, max(0.0, score)), 2)


# -------------------------------------------------------------------
# 9. OVERALL ATS SCORE (MAXIMUM 100)
# -------------------------------------------------------------------

def calculate_overall_score(
    text: str,
    parsed_resume: Dict,
    skills: List[str],
    keywords: List[str],
    action_verbs: List[str],
    skill_validation_results: Dict,
    grammar_results: Dict,
    location_results: Dict,
    jd_keywords: Optional[List[str]] = None,
    experience_months: int = 0,
) -> Dict:
    parsed_resume = parsed_resume or {}
    skills = skills or []
    keywords = keywords or []
    action_verbs = action_verbs or []
    skill_validation_results = skill_validation_results or {}
    grammar_results = grammar_results or {}
    location_results = location_results or {}

    formatting_score = _calc_formatting_score(parsed_resume, text)
    keywords_score = _calc_keywords_score(keywords, skills, jd_keywords)
    content_score = _calc_content_score(text, action_verbs, grammar_results)
    skill_validation_score = _calc_skill_validation_score(
        skill_validation_results
    )
    ats_compatibility_score = _calc_ats_compatibility_score(
        text,
        location_results,
        parsed_resume,
    )

    component_max = {
        "formatting": 20.0,
        "keywords": 25.0,
        "content": 25.0,
        "skill_validation": 15.0,
        "ats_compatibility": 15.0,
    }

    formatting_pct = formatting_score / component_max["formatting"] * 100
    keywords_pct = keywords_score / component_max["keywords"] * 100
    content_pct = content_score / component_max["content"] * 100
    validation_pct_score = (
        skill_validation_score / component_max["skill_validation"] * 100
    )
    ats_compatibility_pct = (
        ats_compatibility_score / component_max["ats_compatibility"] * 100
    )

    skills_keywords_pct = (
        keywords_pct * 0.6
        + validation_pct_score * 0.4
    )

    base_score = (
        skills_keywords_pct * 0.40
        + content_pct * 0.30
        + formatting_pct * 0.15
        + ats_compatibility_pct * 0.15
    )

    penalties = {}
    bonuses = {}
    score = base_score

    grammar_penalty = float(grammar_results.get("penalty_applied", 0.0) or 0.0)
    location_penalty = float(location_results.get("penalty_applied", 0.0) or 0.0)

    if grammar_penalty > 0:
        penalties["grammar"] = grammar_penalty

    if location_penalty > 0:
        penalties["location_privacy"] = location_penalty

    validation_percentage = float(
        skill_validation_results.get("validation_percentage", 0.0) or 0.0
    )

    if validation_percentage >= 0.9:
        bonuses["excellent_skill_validation"] = 2.0
        score += 2.0
    elif validation_percentage >= 0.8:
        bonuses["good_skill_validation"] = 1.0
        score += 1.0

    if grammar_results.get("total_errors", 0) == 0:
        bonuses["perfect_grammar"] = 1.0
        score += 1.0

    if jd_keywords:
        resume_terms = list(dict.fromkeys(keywords + skills))

        fuzzy_result = fuzzy_match_keywords(
            resume_terms,
            jd_keywords,
            threshold=80,
        )

        missing_count = len(fuzzy_result.get("missing", []))
        missing_percentage = min(1.0, missing_count / len(jd_keywords))

        if missing_percentage > 0.7:
            penalties["missing_jd_keywords"] = 15.0
            score -= 15.0
        elif missing_percentage > 0.5:
            penalties["missing_jd_keywords"] = 10.0
            score -= 10.0
        elif missing_percentage > 0.3:
            penalties["missing_jd_keywords"] = 5.0
            score -= 5.0

    overall_score = round(min(100.0, max(0.0, score)), 1)

    return {
        "overall_score": overall_score,
        "formatting_score": round(formatting_score, 1),
        "keywords_score": round(keywords_score, 1),
        "content_score": round(content_score, 1),
        "skill_validation_score": round(skill_validation_score, 1),
        "ats_compatibility_score": round(ats_compatibility_score, 1),
        "overall_interpretation": _generate_score_interpretation(
            overall_score
        ),
        "penalties": penalties,
        "bonuses": bonuses,
    }


# -------------------------------------------------------------------
# 10. STRENGTHS
# -------------------------------------------------------------------

def generate_strengths(
    score_results: Dict,
    skill_validation_results: Dict,
    grammar_results: Dict,
) -> List[str]:
    strengths = []

    if score_results.get("formatting_score", 0) >= 16:
        strengths.append(
            "Well-structured resume with clear sections and bullet points."
        )

    if score_results.get("keywords_score", 0) >= 20:
        strengths.append(
            "Strong keyword optimization and skills presence."
        )

    if score_results.get("content_score", 0) >= 20:
        strengths.append(
            "Good use of action verbs and quantifiable achievements."
        )

    if score_results.get("skill_validation_score", 0) >= 12:
        percentage = (
            skill_validation_results.get("validation_percentage", 0) * 100
        )
        strengths.append(
            f"{percentage:.0f}% of listed skills have supporting evidence."
        )

    if score_results.get("ats_compatibility_score", 0) >= 13:
        strengths.append(
            "Good ATS compatibility with relatively clean formatting."
        )

    if grammar_results.get("total_errors", 0) == 0:
        strengths.append("No grammar or spelling errors were reported.")

    if not strengths:
        strengths.append(
            "Your resume has potential. Review the recommendations below."
        )

    return strengths


# -------------------------------------------------------------------
# 11. CRITICAL ISSUES
# -------------------------------------------------------------------

def generate_critical_issues(
    score_results: Dict,
    grammar_results: Dict,
    location_results: Dict,
) -> List[str]:
    issues = []

    critical_errors = len(grammar_results.get("critical_errors", []))

    if critical_errors > 0:
        issues.append(
            f"{critical_errors} critical grammar or spelling error(s) detected."
        )

    if location_results.get("privacy_risk") == "high":
        issues.append(
            "High privacy risk: remove detailed address information."
        )

    if score_results.get("formatting_score", 0) < 10:
        issues.append(
            "Poor formatting: improve section structure and bullet points."
        )

    if score_results.get("keywords_score", 0) < 12:
        issues.append(
            "Insufficient relevant keywords or listed skills."
        )

    if score_results.get("skill_validation_score", 0) < 7:
        issues.append(
            "Many listed skills lack supporting evidence in projects or experience."
        )

    return issues


# -------------------------------------------------------------------
# 12. ACTIONABLE IMPROVEMENTS
# -------------------------------------------------------------------

def generate_improvements(
    score_results: Dict,
    skill_validation_results: Dict,
) -> List[str]:
    improvements = []

    formatting = score_results.get("formatting_score", 0)
    keywords = score_results.get("keywords_score", 0)
    content = score_results.get("content_score", 0)
    validation = score_results.get("skill_validation_score", 0)
    compatibility = score_results.get("ats_compatibility_score", 0)

    if 12 <= formatting < 16:
        improvements.append(
            "Add relevant bullet points and improve section organization."
        )

    if 14 <= keywords < 20:
        improvements.append(
            "Include relevant job-description keywords where they accurately "
            "reflect your experience."
        )

    if 14 <= content < 20:
        improvements.append(
            "Strengthen project and experience descriptions with measurable "
            "results where you have genuine evidence."
        )

    if 7 <= validation < 12:
        unvalidated_count = len(
            skill_validation_results.get("unvalidated_skills", [])
        )
        improvements.append(
            f"Add genuine supporting project or experience evidence for "
            f"{unvalidated_count} unvalidated skill(s)."
        )

    if 9 <= compatibility < 13:
        improvements.append(
            "Simplify formatting and use standard resume section headings."
        )

    return improvements


# -------------------------------------------------------------------
# 13. SCORE INTERPRETATION
# -------------------------------------------------------------------

def _generate_score_interpretation(overall_score: float) -> str:
    if overall_score >= 90:
        return "Excellent! Your resume is highly optimized for ATS systems."
    if overall_score >= 80:
        return "Great! Your resume should perform well with many ATS systems."
    if overall_score >= 70:
        return "Good! Your resume is ATS-friendly, with room for improvement."
    if overall_score >= 60:
        return "Fair. Your resume needs improvements to be more ATS-compatible."
    if overall_score >= 50:
        return "Below average. Significant improvements are recommended."
    return "Poor. Your resume requires substantial improvements."
