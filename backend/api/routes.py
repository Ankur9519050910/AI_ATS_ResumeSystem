import logging
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import Response

from backend.api.auth import get_current_user
from backend.models.schemas import (
    AnalysisResponse,
    ComponentScores,
    JDComparison,
    SkillValidationDetails,
)

logger = logging.getLogger("ats_resume_scorer")

router = APIRouter(
    prefix="/api/v1",
    tags=["Analysis"],
)


def _clean(text: str) -> str:
    """Remove common emoji prefixes from text."""

    for prefix in (
        "✅",
        "🌟",
        "❌",
        "⚠️",
        "📝",
        "🔴",
        "🟡",
        "🟢",
        "🟠",
        "👍",
    ):
        text = text.lstrip(prefix)

    return text.strip()


# ============================================================
# ANALYZE RESUME
# ============================================================

@router.post(
    "/analyze-resume",
    response_model=AnalysisResponse,
)
async def analyze_resume(
    request: Request,
    resume: UploadFile = File(
        ...,
        description="Resume file — PDF or DOCX, max 5 MB",
    ),
    job_description: str = Form(
        "",
        description="Job description text (optional)",
    ),
    user_id: str = Depends(get_current_user),
):

    warnings: List[str] = []

    # --------------------------------------------------------
    # Load models
    # --------------------------------------------------------

    nlp = request.app.state.nlp
    embedder = request.app.state.embedder

    # --------------------------------------------------------
    # Parse uploaded resume
    # --------------------------------------------------------

    try:

        file_bytes = await resume.read()

        filename = resume.filename or "resume"

        from backend.services.resume_parser import (
            parse_resume_file,
        )

        resume_text, _metadata = parse_resume_file(
            file_bytes,
            filename,
        )

        logger.info(
            f"Parsed '{filename}': "
            f"{len(resume_text)} chars extracted"
        )

    except Exception as exc:

        logger.error(
            f"File parsing failed: {exc}"
        )

        raise HTTPException(
            status_code=422,
            detail=(
                f"Could not read or parse the resume: {exc}"
            ),
        )

    # --------------------------------------------------------
    # Full analysis pipeline
    # --------------------------------------------------------

    try:

        from backend.services.resume_analyzer import (
            analyze_full_resume,
        )

        result = analyze_full_resume(
            resume_text=resume_text,
            nlp=nlp,
            embedder=embedder,
            job_description=job_description,
        )

    except Exception as exc:

        logger.error(
            f"Full analysis pipeline failed: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Analysis pipeline failed: {exc}"
            ),
        )

    # ========================================================
    # JD MATCH ANALYSIS
    # ========================================================

    jd_comparison_result = None

    jd_result = result.get(
        "jd_match_analysis"
    )

    if jd_result:

        try:

            jd_comparison_result = JDComparison(
                match_percentage=round(
                    float(
                        jd_result.get(
                            "match_percentage",
                            0.0,
                        )
                    ),
                    1,
                ),

                semantic_similarity=round(
                    float(
                        jd_result.get(
                            "semantic_similarity",
                            0.0,
                        )
                    ),
                    3,
                ),

                matched_keywords=jd_result.get(
                    "matched_keywords",
                    [],
                )[:20],

                missing_keywords=jd_result.get(
                    "missing_keywords",
                    [],
                )[:15],

                skills_gap=jd_result.get(
                    "skills_gap",
                    [],
                )[:10],
            )

        except Exception as exc:

            logger.error(
                f"Failed to process JD comparison: {exc}"
            )

            warnings.append(
                "Job description comparison could not be processed."
            )

            jd_comparison_result = None

    # ========================================================
    # DETAILED FEEDBACK
    # ========================================================

    detailed_fb = result.get(
        "detailed_feedback",
        [],
    )

    # ========================================================
    # SKILL VALIDATION DETAILS
    # ========================================================

    svd_raw = result.get(
        "skill_validation_details"
    ) or {}

    skill_val_details = SkillValidationDetails(
        validated=svd_raw.get(
            "validated",
            [],
        ),

        unvalidated=svd_raw.get(
            "unvalidated",
            [],
        ),

        total=svd_raw.get(
            "total",
            0,
        ),

        validated_count=svd_raw.get(
            "validated_count",
            0,
        ),

        validation_pct=svd_raw.get(
            "validation_pct",
            0.0,
        ),
    )

    # ========================================================
    # KEYWORD MATCH
    # ========================================================

    if jd_comparison_result:

        keyword_match = (
            jd_comparison_result.match_percentage
        )

    else:

        # No JD means there is nothing to compare
        # the resume against.
        keyword_match = 0.0

    # ========================================================
    # FINAL API RESPONSE
    # ========================================================

    response = AnalysisResponse(

        # Main ATS score
        ats_score=result.get(
            "ats_score",
            0.0,
        ),

        # Component scores
        component_scores=ComponentScores(
            **result.get(
                "component_scores",
                {
                    "formatting": 0.0,
                    "keywords": 0.0,
                    "content": 0.0,
                    "skill_validation": 0.0,
                    "ats_compatibility": 0.0,
                },
            )
        ),

        # Issues
        issues_summary=result.get(
            "issues_summary",
            [],
        ),

        detailed_feedback=detailed_fb,

        # JD analysis
        jd_match_analysis=jd_comparison_result,

        # Skill validation
        skill_validation_details=skill_val_details,

        # Keyword match
        keyword_match=keyword_match,

        # Keywords
        missing_keywords=result.get(
            "missing_keywords",
            [],
        ),

        matched_keywords=result.get(
            "matched_keywords",
            [],
        ),

        # Skills
        skills=list(
            result.get(
                "skills",
                [],
            )[:20]
        ),

        # Suggestions
        suggestions=result.get(
            "suggestions",
            [],
        ),

        # Strengths
        strengths=result.get(
            "strengths",
            [],
        ),

        # Critical issues
        critical_issues=result.get(
            "critical_issues",
            [],
        ),

        # Warnings
        warnings=warnings,

        # Interpretation
        interpretation=result.get(
            "interpretation",
            "",
        ),
    )

    # ========================================================
    # SAVE ANALYSIS TO SUPABASE
    # ========================================================

    try:

        from backend.database.supabase_db import (
            save_analysis,
        )

        await save_analysis(
            user_id,
            filename,
            result,
        )

    except Exception as exc:

        # Saving history should not break the analysis.
        logger.warning(
            f"History save failed (non-blocking): {exc}"
        )

    return response


# ============================================================
# HEALTH CHECK
# ============================================================

@router.get("/health")
async def health_check(
    request: Request,
):

    """Health check — confirms models are loaded."""

    return {
        "status": "healthy",

        "nlp_loaded": (
            request.app.state.nlp is not None
        ),

        "embedder_loaded": (
            request.app.state.embedder is not None
        ),
    }


# ============================================================
# GET USER HISTORY
# ============================================================

@router.get("/history")
async def get_history(
    user_id: str = Depends(get_current_user),
):

    """Return the signed-in user's analysis history."""

    from backend.database.supabase_db import (
        get_user_history,
    )

    try:

        return await get_user_history(
            user_id
        )

    except Exception as exc:

        logger.error(
            f"History fetch failed: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not load history: {exc}"
            ),
        )


# ============================================================
# DELETE HISTORY ENTRY
# ============================================================

@router.delete(
    "/history/{analysis_id}"
)
async def delete_history_entry(
    analysis_id: str,
    user_id: str = Depends(get_current_user),
):

    """Delete one analysis from the signed-in user's history."""

    from backend.database.supabase_db import (
        delete_analysis,
    )

    try:

        success = await delete_analysis(
            analysis_id,
            user_id,
        )

        if not success:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Analysis not found or "
                    "not owned by this user."
                ),
            )

        return {
            "status": "deleted",
            "id": analysis_id,
        }

    except HTTPException:

        raise

    except Exception as exc:

        logger.error(
            f"History delete failed: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=f"Could not delete: {exc}",
        )


# ============================================================
# GENERATE PDF
# ============================================================

@router.post("/generate-pdf")
async def generate_pdf(
    data: AnalysisResponse,
    user_id: str = Depends(get_current_user),
):

    from backend.services.report_generator import (
        generate_html_reports,
    )

    from backend.services.pdf_export import (
        generate_combined_pdf,
    )

    try:

        html_docs = generate_html_reports(
            data.model_dump()
        )

        pdf_bytes = generate_combined_pdf(
            html_docs
        )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    "attachment; "
                    "filename=ats_report.pdf"
                )
            },
        )

    except Exception as exc:

        logger.error(
            f"Failed to generate PDF: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to generate PDF: {exc}"
            ),
        )


# ============================================================
# GENERATE HISTORY PDF
# ============================================================

@router.get(
    "/history/{analysis_id}/pdf"
)
async def generate_history_pdf(
    analysis_id: str,
    user_id: str = Depends(get_current_user),
):

    from backend.database.supabase_db import (
        get_user_history,
    )

    from backend.services.report_generator import (
        generate_html_reports,
    )

    from backend.services.pdf_export import (
        generate_combined_pdf,
    )

    history = await get_user_history(
        user_id
    )

    analysis_data = next(
        (
            item["analysis_result"]
            for item in history
            if item["id"] == analysis_id
        ),
        None,
    )

    if not analysis_data:

        raise HTTPException(
            status_code=404,
            detail="Analysis not found",
        )

    try:

        html_docs = generate_html_reports(
            analysis_data
        )

        pdf_bytes = generate_combined_pdf(
            html_docs
        )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f"attachment; "
                    f"filename=ats_report_{analysis_id}.pdf"
                )
            },
        )

    except Exception as exc:

        logger.error(
            f"Failed to generate PDF for history: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to generate PDF: {exc}"
            ),
        )