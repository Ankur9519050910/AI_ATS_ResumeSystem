
import json
import logging
import os
from typing import Dict, Optional

from groq import Groq

logger = logging.getLogger("ats_resume_scorer")

GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

_client = None


def _get_client() -> Groq:
    """Create the Groq client once and reuse it."""
    global _client

    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError(
                "GROQ_API_KEY environment variable not set"
            )

        _client = Groq(api_key=api_key)

    return _client


# ============================================================
# RESUME PROMPTS
# ============================================================

RESUME_SYSTEM_PROMPT = """
You are a precise resume parser.
Extract information only from the supplied resume.
Return one valid JSON object only.
Do not include explanations or Markdown.
Never invent skills, qualifications, experience, or metrics.
"""


RESUME_USER_PROMPT = """
Extract the information from this resume into the JSON structure below.

{{
    "name": "",
    "email": null,
    "phone": null,
    "linkedin": null,
    "github": null,
    "professional_summary": "",
    "skills": [],
    "experience": [
        {{
            "job_title": "",
            "company": "",
            "start_date": "",
            "end_date": "",
            "duration_months": 0,
            "description": ""
        }}
    ],
    "education": [
        {{
            "degree": "",
            "institution": "",
            "year": ""
        }}
    ],
    "certifications": [],
    "projects": [
        {{
            "title": "",
            "description": "",
            "technologies": []
        }}
    ],
    "action_verbs": [],
    "keywords": []
}}

Instructions:
- Extract technical skills and soft skills explicitly listed in the resume.
- Extract technologies actually used in projects and experience.
- Preserve meaningful multiword skills, including C++, React.js,
  Object-Oriented Programming, Data Structures and Algorithms,
  Database Management Systems, and VS Code extension development.
- Include important algorithms, frameworks, tools, and technical concepts
  in keywords when supported by the resume.
- Extract measurable achievements accurately when present.
- Preserve project descriptions and their technologies.
- Do not invent skills, metrics, responsibilities, or qualifications.
- Use empty strings, empty lists, or null for unavailable values,
  according to the expected field type.
- Return valid JSON only, without Markdown fences.

Resume text:
{raw_text}
"""


# ============================================================
# JOB DESCRIPTION PROMPTS
# ============================================================

JD_SYSTEM_PROMPT = """
You are a precise job-description parser.
Extract only information supported by the supplied job description.
Return one valid JSON object only.
Do not include explanations or Markdown.
"""


JD_USER_PROMPT = """
Extract the information from this job description into the JSON structure.

{{
    "job_title": "",
    "required_skills": [],
    "preferred_skills": [],
    "jd_skills": [],
    "experience_required": "",
    "education_required": "",
    "key_responsibilities": [],
    "keywords": []
}}

Instructions:
- required_skills: technical skills explicitly required by the role.
- preferred_skills: technical skills explicitly preferred or optional.
- jd_skills: unique, complete technical skills required or preferred.
- Include skills such as programming languages, frameworks, libraries,
  databases, algorithms, tools, and technical concepts when explicitly
  mentioned.
- Preserve complete multiword terms, for example:
  "VS Code extension development", "Asynchronous JavaScript",
  "Search algorithms", and "Frontend performance optimization".
- Do not return fragments such as "VS" when the source says "VS Code".
- Do not treat generic sentence fragments, locations, or company names
  as technical skills.
- keywords: include relevant technologies, tools, algorithms,
  qualifications, and domain-specific phrases.
- Keep qualifications and general keywords separate from technical skills.
- Do not invent requirements.
- Use empty strings or empty lists for unavailable fields.
- Return valid JSON only, without Markdown fences.

Job description:
{raw_text}
"""


# ============================================================
# GROQ REQUEST
# ============================================================

def _call_groq(
    client: Groq,
    system_prompt: str,
    user_prompt: str,
) -> str:
    """Send a request to Groq and return its text response."""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        temperature=0.0,
        max_tokens=4096,
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError("Groq returned an empty response.")

    return content.strip()


# ============================================================
# JSON PARSING
# ============================================================

def _try_parse_json(text: str) -> Optional[dict]:
    """Parse a JSON object, allowing optional Markdown fences."""

    cleaned = text.strip()

    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")

        if first_newline != -1:
            cleaned = cleaned[first_newline + 1:]

        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3]

        cleaned = cleaned.strip()

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        return None

    if not isinstance(result, dict):
        return None

    return result


def _parse_with_retry(
    system_prompt: str,
    prompt: str,
    document_type: str,
) -> dict:
    """Call Groq and retry once if the response is invalid JSON."""

    client = _get_client()

    raw_response = _call_groq(
        client,
        system_prompt,
        prompt,
    )

    result = _try_parse_json(raw_response)

    if result is not None:
        return result

    logger.warning(
        "Groq %s parser returned invalid JSON; retrying.",
        document_type,
    )

    strict_prompt = (
        "Return one valid raw JSON object only. "
        "Do not include Markdown fences or explanations.\n\n"
        + prompt
    )

    raw_response = _call_groq(
        client,
        system_prompt,
        strict_prompt,
    )

    result = _try_parse_json(raw_response)

    if result is not None:
        return result

    # Do not log API keys or the entire resume/JD.
    logger.error(
        "Groq returned invalid JSON for %s after retry.",
        document_type,
    )

    raise ValueError(
        f"Groq returned invalid JSON for {document_type} "
        "after retry."
    )


# ============================================================
# SHARED VALIDATION HELPERS
# ============================================================

def _clean_string_list(value) -> list:
    """Clean a list of strings and remove exact duplicates."""

    if not isinstance(value, list):
        return []

    cleaned = []
    seen = set()

    for item in value:
        if not isinstance(item, str):
            continue

        item = " ".join(item.split())

        if not item:
            continue

        canonical = item.casefold()

        if canonical in seen:
            continue

        seen.add(canonical)
        cleaned.append(item)

    return cleaned


def _clean_string(value, default: str = "") -> str:
    """Return a normalized string or its default."""

    if not isinstance(value, str):
        return default

    return " ".join(value.split())


# ============================================================
# RESUME VALIDATION
# ============================================================

def _validate_resume_result(result: dict) -> dict:
    """Ensure the parsed resume has all expected fields."""

    if not isinstance(result, dict):
        result = {}

    defaults = {
        "name": "",
        "email": None,
        "phone": None,
        "linkedin": None,
        "github": None,
        "professional_summary": "",
        "skills": [],
        "experience": [],
        "education": [],
        "certifications": [],
        "projects": [],
        "action_verbs": [],
        "keywords": [],
    }

    for key, default in defaults.items():
        value = result.get(key)

        if value is None:
            result[key] = default
        elif isinstance(default, list) and not isinstance(value, list):
            result[key] = []
        elif isinstance(default, str) and not isinstance(value, str):
            result[key] = default

    for field in (
        "name",
        "professional_summary",
    ):
        result[field] = _clean_string(result[field])

    for field in (
        "email",
        "phone",
        "linkedin",
        "github",
    ):
        value = result[field]

        if isinstance(value, str):
            result[field] = value.strip() or None
        elif value is not None:
            result[field] = None

    for field in (
        "skills",
        "certifications",
        "action_verbs",
        "keywords",
    ):
        result[field] = _clean_string_list(result[field])

    # Validate experience entries.
    valid_experience = []

    for exp in result["experience"]:
        if not isinstance(exp, dict):
            continue

        cleaned_exp = {
            "job_title": _clean_string(exp.get("job_title")),
            "company": _clean_string(exp.get("company")),
            "start_date": _clean_string(exp.get("start_date")),
            "end_date": _clean_string(exp.get("end_date")),
            "duration_months": 0,
            "description": _clean_string(exp.get("description")),
        }

        try:
            duration = int(exp.get("duration_months", 0))
            cleaned_exp["duration_months"] = max(0, duration)
        except (TypeError, ValueError, OverflowError):
            cleaned_exp["duration_months"] = 0

        valid_experience.append(cleaned_exp)

    result["experience"] = valid_experience

    # Validate project entries.
    valid_projects = []

    for project in result["projects"]:
        if not isinstance(project, dict):
            continue

        valid_projects.append(
            {
                "title": _clean_string(project.get("title")),
                "description": _clean_string(
                    project.get("description")
                ),
                "technologies": _clean_string_list(
                    project.get("technologies")
                ),
            }
        )

    result["projects"] = valid_projects

    # Validate education entries.
    valid_education = []

    for item in result["education"]:
        if not isinstance(item, dict):
            continue

        valid_education.append(
            {
                "degree": _clean_string(item.get("degree")),
                "institution": _clean_string(
                    item.get("institution")
                ),
                "year": _clean_string(item.get("year")),
            }
        )

    result["education"] = valid_education

    return result


# ============================================================
# JOB DESCRIPTION VALIDATION
# ============================================================

def _validate_jd_result(result: dict) -> dict:
    """Validate and normalize parsed job-description data."""

    if not isinstance(result, dict):
        result = {}

    defaults = {
        "job_title": "",
        "required_skills": [],
        "preferred_skills": [],
        "jd_skills": [],
        "experience_required": "",
        "education_required": "",
        "key_responsibilities": [],
        "keywords": [],
    }

    for key, default in defaults.items():
        value = result.get(key)

        if value is None:
            result[key] = default
        elif isinstance(default, list) and not isinstance(value, list):
            result[key] = []
        elif isinstance(default, str) and not isinstance(value, str):
            result[key] = default

    for field in (
        "job_title",
        "experience_required",
        "education_required",
    ):
        result[field] = _clean_string(result[field])

    for field in (
        "required_skills",
        "preferred_skills",
        "jd_skills",
        "key_responsibilities",
        "keywords",
    ):
        result[field] = _clean_string_list(result[field])

    # Build the complete skill list from all structured skill fields.
    # This avoids depending exclusively on the LLM's jd_skills field.
    combined_skills = []
    seen_skills = set()

    for skill in (
        result["required_skills"]
        + result["preferred_skills"]
        + result["jd_skills"]
    ):
        canonical = skill.casefold()

        if canonical not in seen_skills:
            seen_skills.add(canonical)
            combined_skills.append(skill)

    result["jd_skills"] = combined_skills

    return result


# ============================================================
# PUBLIC FUNCTIONS
# ============================================================

def parse_resume(raw_text: str) -> Dict:
    """Parse resume text using Groq."""

    if not isinstance(raw_text, str) or not raw_text.strip():
        raise ValueError("Resume text cannot be empty.")

    prompt = RESUME_USER_PROMPT.format(
        raw_text=raw_text[:30000]
    )

    result = _parse_with_retry(
        RESUME_SYSTEM_PROMPT,
        prompt,
        "resume",
    )

    return _validate_resume_result(result)


def parse_job_description(raw_text: str) -> Dict:
    """Parse job-description text using Groq."""

    if not isinstance(raw_text, str) or not raw_text.strip():
        raise ValueError("Job description text cannot be empty.")

    prompt = JD_USER_PROMPT.format(
        raw_text=raw_text[:30000]
    )

    result = _parse_with_retry(
        JD_SYSTEM_PROMPT,
        prompt,
        "job description",
    )

    return _validate_jd_result(result)
