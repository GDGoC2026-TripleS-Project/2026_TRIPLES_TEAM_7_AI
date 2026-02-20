from __future__ import annotations
from fastapi import HTTPException

from match_ai.schemas.schemas import JobInfo, MatchResponse, MatchItem
from match_ai.services.scorer import fetch_pdf_text, extract_resume_keywords, calc_match_percent, build_match_context
from match_ai.services.groq_client import generate_comments


async def analyze_match(file_url: str, job: JobInfo) -> MatchResponse:
    try:
        resume_text = await fetch_pdf_text(file_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF 다운로드/추출 실패: {e}")

    resume_keywords = extract_resume_keywords(resume_text)
    match_percent = calc_match_percent(job, resume_keywords)
    ctx = build_match_context(job, resume_keywords)
    comments = await generate_comments(ctx, match_percent)

    return MatchResponse(
        matchPercent=match_percent,
        strengthTop3=[MatchItem(**item) for item in comments["strengthTop3"]],
        gapTop3=[MatchItem(**item) for item in comments["gapTop3"]],
        riskTop3=[MatchItem(**item) for item in comments["riskTop3"]],
    )
