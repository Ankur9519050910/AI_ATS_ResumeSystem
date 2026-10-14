
import re
from typing import Dict, List

from rapidfuzz import fuzz


SKILL_ALIASES: Dict[str, str] = {
    # Programming languages
    "js": "javascript",
    "javascript": "javascript",
    "typescript": "typescript",
    "ts": "typescript",
    "c plus plus": "c++",
    "cpp": "c++",
    "c++": "c++",
    "c sharp": "c#",
    "c#": "c#",
    "golang": "go",

    # Frontend frameworks
    "reactjs": "react",
    "react.js": "react",
    "react": "react",
    "angularjs": "angular",
    "vuejs": "vue",
    "vue.js": "vue",
    "nextjs": "next.js",
    "next": "next.js",
    "tailwindcss": "tailwind",
    "tailwind css": "tailwind",

    # Backend
    "nodejs": "node.js",
    "node": "node.js",
    "expressjs": "express",
    "express.js": "express",
    "springboot": "spring boot",

    # AI and data
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "sklearn": "scikit-learn",
    "huggingface": "hugging face",
    "pyspark": "spark",

    # Cloud and infrastructure
    "amazon web services": "aws",
    "google cloud": "gcp",
    "google cloud platform": "gcp",
    "k8s": "kubernetes",
    "dotnet": ".net",

    # Databases
    "postgres": "postgresql",
    "database management systems": "dbms",

    # Computer science concepts
    "data structures and algorithms": "dsa",
    "data structures algorithms": "dsa",
    "dsa": "dsa",
    "object oriented programming": "oop",
    "object-oriented programming": "oop",
    "oop": "oop",
}


def normalize_skill(skill: str) -> str:
    """
    Normalize capitalization, aliases, and common spelling variations.

    Examples:
        React.js -> react
        ReactJS -> react
        Node.js -> node.js
        JavaScript -> javascript
        DBMS -> dbms
        Data Structures and Algorithms (DSA) -> dsa
        Object-Oriented Programming (OOP) -> oop
    """
    if not isinstance(skill, str):
        return ""

    cleaned = skill.lower().strip()
    cleaned = cleaned.replace("&", " and ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.strip(" \t\r\n,;:()[]{}\"'`")

    # Remove known abbreviations in parentheses before normalization.
    # This handles forms such as "Data Structures and Algorithms (DSA)".
    without_abbreviation = re.sub(
        r"\s*\((?:dsa|oop|dbms|os|ai|ml|nlp|cv)\)\s*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()

    # Try the full form first, then the form without its abbreviation.
    for candidate in (cleaned, without_abbreviation):
        candidate = re.sub(r"\s+", " ", candidate).strip()

        if candidate in SKILL_ALIASES:
            return SKILL_ALIASES[candidate]

        compact = re.sub(r"[\s._-]+", "", candidate)

        if compact in SKILL_ALIASES:
            return SKILL_ALIASES[compact]

    return without_abbreviation or cleaned


def _unique_by_normalized_name(items: List[str]) -> List[str]:
    """Deduplicate by canonical name while preserving the first spelling."""
    unique_items = []
    seen = set()

    for item in items or []:
        if not isinstance(item, str) or not item.strip():
            continue

        original = item.strip()
        canonical = normalize_skill(original)

        if not canonical or canonical in seen:
            continue

        seen.add(canonical)
        unique_items.append(original)

    return unique_items


def _similarity_score(first: str, second: str) -> int:
    """Calculate fuzzy similarity for non-identical, sufficiently long terms."""
    if not first or not second:
        return 0

    # Avoid fuzzy matching short terms like C, R, Go, or AI.
    if len(first) < 4 or len(second) < 4:
        return 0

    return max(
        fuzz.ratio(first, second),
        fuzz.token_sort_ratio(first, second),
    )


def fuzzy_match_keywords(
    resume_keywords: List[str],
    jd_keywords: List[str],
    threshold: int = 85,
) -> Dict[str, List[str]]:
    """
    Match job-description keywords against resume keywords.

    - Normalizes aliases before matching.
    - Removes case and alias duplicates from both lists.
    - Uses exact canonical matches first.
    - Uses fuzzy matching only for longer terms.
    - Preserves the first original spelling for display.
    """
    resume_items = _unique_by_normalized_name(resume_keywords or [])
    jd_items = _unique_by_normalized_name(jd_keywords or [])

    resume_normalized = [
        normalize_skill(item)
        for item in resume_items
    ]

    matched = []
    missing = []

    for jd_original in jd_items:
        jd_canonical = normalize_skill(jd_original)

        # Exact canonical match.
        if jd_canonical in resume_normalized:
            matched.append(jd_original)
            continue

        best_score = max(
            (
                _similarity_score(jd_canonical, resume_canonical)
                for resume_canonical in resume_normalized
            ),
            default=0,
        )

        if best_score >= threshold:
            matched.append(jd_original)
        else:
            missing.append(jd_original)

    return {
        "matched": matched,
        "missing": missing,
    }
