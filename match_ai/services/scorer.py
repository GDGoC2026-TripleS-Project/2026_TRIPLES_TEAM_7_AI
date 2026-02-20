from __future__ import annotations
from typing import List, Tuple
import io

import httpx
import pdfplumber
from konlpy.tag import Okt
from rapidfuzz import fuzz

from match_ai.schemas.schemas import JobInfo

okt = Okt()


async def fetch_pdf_text(url: str) -> str:
    async with httpx.AsyncClient(follow_redirects=True) as http:
        resp = await http.get(url, timeout=30)
        resp.raise_for_status()
        pdf_bytes = resp.content

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return " ".join(page.extract_text() or "" for page in pdf.pages)


def extract_resume_keywords(text: str) -> List[str]:
    nouns = okt.nouns(text)
    raw_tokens = text.split()
    return list(set(nouns + raw_tokens))


def is_matched(keyword: str, resume_keywords: List[str], threshold: int = 75) -> bool:
    kw = keyword.lower().strip()
    for rk in resume_keywords:
        if fuzz.partial_ratio(kw, rk.lower().strip()) >= threshold:
            return True
    return False


def classify_keywords(
    keywords: List[str],
    resume_keywords: List[str],
) -> Tuple[List[str], List[str]]:
    matched = [k for k in keywords if is_matched(k, resume_keywords)]
    unmatched = [k for k in keywords if not is_matched(k, resume_keywords)]
    return matched, unmatched


def calc_match_percent(job: JobInfo, resume_keywords: List[str]) -> int:
    def match_rate(keywords: List[str]) -> float:
        if not keywords:
            return 1.0
        matched = sum(1 for k in keywords if is_matched(k, resume_keywords))
        return matched / len(keywords)

    score = (
        match_rate(job.necessaryStack) * 0.60
        + match_rate(job.preferStack)  * 0.25
        + match_rate(job.roleText)     * 0.15
    )
    return round(score * 100)


def build_match_context(job: JobInfo, resume_keywords: List[str]) -> dict:
    necessary_matched, necessary_unmatched = classify_keywords(job.necessaryStack, resume_keywords)
    prefer_matched, prefer_unmatched = classify_keywords(job.preferStack, resume_keywords)
    role_matched, role_unmatched = classify_keywords(job.roleText, resume_keywords)

    return {
        "necessary_matched": necessary_matched,
        "necessary_unmatched": necessary_unmatched,
        "prefer_matched": prefer_matched,
        "prefer_unmatched": prefer_unmatched,
        "role_matched": role_matched,
        "role_unmatched": role_unmatched,
        "experienceLevel": job.experienceLevel,
        "employmentType": job.employmentType,
        "locationText": job.locationText,
        "workDay": job.workDay,
    }
