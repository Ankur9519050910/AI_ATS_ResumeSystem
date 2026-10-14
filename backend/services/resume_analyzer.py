
import logging
import re
from typing import Dict, List, Optional

import spacy
from sentence_transformers import SentenceTransformer

from backend.services.groq_parser import (
    parse_resume,
    parse_job_description,
)
from backend.services.jd_matcher import compare_resume_with_jd
from backend.services.feedback_engine import (
    analyze_issues,
    generate_issues_summary,
)
from backend.services.ats_scorer import (
    calculate_overall_score,
    validate_skills_with_projects,
)


logger = logging.getLogger("ats_resume_scorer")


def _unique_strings(*groups: List[str]) -> List[str]:
    """Combine string lists while preserving order and removing duplicates."""
    result = []
    seen = set()

    for group in groups:
        for item in group or []:
            if not isinstance(item, str):
                continue

            item = " ".join(item.split())
            if not item:
                continue

            key = item.casefold()

            if key not in seen:
                seen.add(key)
                result.append(item)

    return result


def _has_quantifiable_achievement(parsed_resume: Dict) -> bool:
    """Check whether project or experience descriptions contain measurable evidence."""
    sections = []

    for project in parsed_resume.get("projects", []):
        if isinstance(project, dict):
            sections.append(project.get("description", ""))

    for experience in parsed_resume.get("experience", []):
        if isinstance(experience, dict):
            sections.append(experience.get("description", ""))

    # Match numbers, percentages, currency amounts, and numeric quantities.
    metric_pattern = re.compile(
        r"""
        (?<!\w)
        (?:
            \d+(?:\.\d+)?\s*%
            |
            [$₹€£]\s*\d[\d,]*(?:\.\d+)?
            |
            \d[\d,]*(?:\.\d+)?
            \s*
            (?:\+|x|X)?
            \s*
            (?:users?|records?|requests?|students?|projects?|
               algorithms?|cities|ms|milliseconds?|seconds?|
               minutes?|hours?|days?|months?|years?|members?|
               problems?|percent|per\s+cent)
            \b
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    return any(
        isinstance(text, str) and metric_pattern.search(text)
        for text in sections
    )


def analyze_full_resume(
    resume_text: str,
    nlp: spacy.Language,
    embedder: SentenceTransformer,
    job_description: Optional[str] = None,
) -> Dict:
    """Run resume parsing, skill validation, scoring, and JD comparison."""

    if not isinstance(resume_text, str) or not resume_text.strip():
        raise ValueError("Resume text cannot be empty.")

    # ---------------------------------------------------------
    # 1. Parse resume
    # ---------------------------------------------------------
    parsed_resume = parse_resume(resume_text)

    logger.info(
        "Groq parsed summary: %r",
        parsed_resume.get("professional_summary", "")[:100],
    )
    logger.info(
        "Groq parsed skills count: %d",
        len(parsed_resume.get("skills", [])),
    )
    logger.info(
        "Groq parsed experience count: %d",
        len(parsed_resume.get("experience", [])),
    )

    # ---------------------------------------------------------
    # 2. Extract resume information
    # ---------------------------------------------------------
    skills = parsed_resume.get("skills", [])
    projects = parsed_resume.get("projects", [])
    keywords = parsed_resume.get("keywords", [])
    action_verbs = parsed_resume.get("action_verbs", [])

    # ---------------------------------------------------------
    # 3. Calculate experience
    # ---------------------------------------------------------
    experience_months = 0

    for entry in parsed_resume.get("experience", []):
        if not isinstance(entry, dict):
            continue

        try:
            experience_months += max(
                0, int(entry.get("duration_months", 0))
            )
        except (TypeError, ValueError, OverflowError):
            continue

    # ---------------------------------------------------------
    # 4. Contact information
    # ---------------------------------------------------------
    contact_info = {
        "email": parsed_resume.get("email"),
        "phone": parsed_resume.get("phone"),
        "linkedin": parsed_resume.get("linkedin"),
        "github": parsed_resume.get("github"),
        "portfolio": None,
    }

    # ---------------------------------------------------------
    # 5. Validate skills against projects and experience
    # ---------------------------------------------------------
    skill_validation = validate_skills_with_projects(
        skills=skills,
        projects=projects,
        experience_entries=parsed_resume.get("experience", []),
        embedder=embedder,
    )

    # ---------------------------------------------------------
    # 6. Job description analysis
    # ---------------------------------------------------------
    jd_comparison_result = None
    jd_keywords = None

    if isinstance(job_description, str) and job_description.strip():
        jd_text = job_description.strip()
        parsed_jd = parse_job_description(jd_text)

        required_skills = parsed_jd.get("required_skills", [])
        preferred_skills = parsed_jd.get("preferred_skills", [])
        structured_jd_skills = parsed_jd.get("jd_skills", [])

        # Use the complete structured skill list. This is important:
        # the matcher should not have to infer technical skills from
        # spaCy entities when structured skills are available.
        jd_skills = _unique_strings(
            required_skills,
            preferred_skills,
            structured_jd_skills,
        )

        # Keep keywords and skills together for keyword overlap scoring.
        jd_keywords = _unique_strings(
            parsed_jd.get("keywords", []),
            required_skills,
            preferred_skills,
            structured_jd_skills,
        )

        logger.info(
            "Parsed JD skills count: %d",
            len(jd_skills),
        )
        logger.info(
            "Parsed JD keywords count: %d",
            len(jd_keywords),
        )

        jd_comparison_result = compare_resume_with_jd(
            resume_text=resume_text,
            resume_keywords=keywords,
            resume_skills=skills,
            jd_text=jd_text,
            jd_keywords=jd_keywords,
            embedder=embedder,
            nlp=nlp,
            jd_skills=jd_skills,
        )

    # ---------------------------------------------------------
    # 7. Default grammar and location results
    # ---------------------------------------------------------
    from backend.utils.file_utils import (
        get_default_grammar_results,
        get_default_location_results,
    )

    grammar_results = get_default_grammar_results()
    location_results = get_default_location_results()

    # ---------------------------------------------------------
    # 8. Calculate ATS scores
    # ---------------------------------------------------------
    scores = calculate_overall_score(
        text=resume_text,
        parsed_resume=parsed_resume,
        skills=skills,
        keywords=keywords,
        action_verbs=action_verbs,
        skill_validation_results=skill_validation,
        grammar_results=grammar_results,
        location_results=location_results,
        jd_keywords=jd_keywords,
        experience_months=experience_months,
    )

    # ---------------------------------------------------------
    # 9. Generate detailed feedback
    # ---------------------------------------------------------
    detailed_feedback = analyze_issues(
        resume_text=resume_text,
        parsed_resume=parsed_resume,
        skills=skills,
        projects=projects,
        action_verbs=action_verbs,
        skill_validation=skill_validation,
        scores=scores,
        contact_info=contact_info,
    )

    issues_summary = generate_issues_summary(detailed_feedback)

    # ---------------------------------------------------------
    # 10. Skill validation details
    # ---------------------------------------------------------
    validated_raw = skill_validation.get("validated_skills", [])
    unvalidated_raw = skill_validation.get("unvalidated_skills", [])

    total_skills = len(validated_raw) + len(unvalidated_raw)

    validation_pct = round(
        len(validated_raw) / total_skills * 100,
        1,
    ) if total_skills else 0.0

    skill_validation_details = {
        "validated": [
            {
                "skill": item.get("skill"),
                "projects": item.get("projects", []),
            }
            for item in validated_raw
            if isinstance(item, dict)
        ],
        "unvalidated": unvalidated_raw,
        "total": total_skills,
        "validated_count": len(validated_raw),
        "validation_pct": validation_pct,
    }

    # ---------------------------------------------------------
    # 11. Matched and missing keywords
    # ---------------------------------------------------------
    if jd_comparison_result:
        matched_keywords = jd_comparison_result.get(
            "matched_keywords", []
        )
        missing_keywords = jd_comparison_result.get(
            "missing_keywords", []
        )
    else:
        matched_keywords = list(keywords[:20])
        missing_keywords = []

    # ---------------------------------------------------------
    # 12. Generate strengths
    # ---------------------------------------------------------
    strengths = _generate_strengths(
        parsed_resume=parsed_resume,
        skills=skills,
        projects=projects,
        action_verbs=action_verbs,
        skill_validation=skill_validation,
        scores=scores,
    )

    # ---------------------------------------------------------
    # 13. Final analysis response
    # ---------------------------------------------------------
    return {
        "ats_score": scores["overall_score"],
        "component_scores": {
            "formatting": scores["formatting_score"],
            "keywords": scores["keywords_score"],
            "content": scores["content_score"],
            "skill_validation": scores["skill_validation_score"],
            "ats_compatibility": scores["ats_compatibility_score"],
        },
        "issues_summary": issues_summary,
        "detailed_feedback": detailed_feedback,
        "jd_match_analysis": jd_comparison_result,
        "skills": skills,
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "strengths": strengths,
        "interpretation": scores.get("overall_interpretation", ""),
        "skill_validation_details": skill_validation_details,
        "experience_months": experience_months,
    }


def _generate_strengths(
    parsed_resume: Dict,
    skills: List,
    projects: List,
    action_verbs: List,
    skill_validation: Dict,
    scores: Dict,
) -> List[str]:
    """Generate strengths based on structured resume evidence."""

    strengths = []

    if parsed_resume.get("experience"):
        strengths.append("Has a dedicated Experience section")

    if parsed_resume.get("projects") or projects:
        strengths.append(
            "Includes a Projects section showcasing applied skills"
        )

    if parsed_resume.get("education"):
        strengths.append("Education section is present")

    if parsed_resume.get("skills"):
        strengths.append("Clear Skills section with listed technologies")

    summary = parsed_resume.get("professional_summary", "")
    if isinstance(summary, str) and summary.strip():
        strengths.append(
            "Professional Summary provides a quick overview"
        )

    if len(skills) >= 8:
        strengths.append(
            f"Strong skill set — {len(skills)} skills detected"
        )

    if len(action_verbs) >= 5:
        strengths.append(
            f"Uses {len(action_verbs)} strong action verbs in bullet points"
        )

    validated = skill_validation.get("validated_skills", [])

    if len(validated) >= 3:
        strengths.append(
            f"{len(validated)} skills are backed by "
            "project/experience evidence"
        )

    if scores.get("formatting_score", 0) >= 16:
        strengths.append("Well-formatted and ATS-friendly structure")

    if _has_quantifiable_achievement(parsed_resume):
        strengths.append(
            "Includes measurable achievements in projects or experience"
        )

    return strengths
