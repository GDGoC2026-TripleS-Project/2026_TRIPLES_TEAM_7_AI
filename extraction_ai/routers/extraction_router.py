from fastapi import APIRouter, HTTPException

from extraction_ai.schemas.schemas import ExtractRequest, JobCardResponse
from extraction_ai.services.extractor import detect_site, crawl, extract_with_ai

router = APIRouter()


@router.post("/api/extract", response_model=JobCardResponse)
async def extract_job(req: ExtractRequest):
    """
    채용공고 URL → 크롤링 + 사이트별 AI 추출 → job_cards ERD 형식 반환
    지원 사이트: wanted.co.kr / jobkorea.co.kr / linkareer.com
    """
    
    print("==== 새 요청 ====")
    #print("요청 헤더:", request.headers)
    #print("요청 바디 raw:", await request.body())
    print("받은 url:", req.url)

    try:
        site = detect_site(req.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        posting = crawl(req.url, site)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"크롤링 실패: {e}")

    if not posting:
        raise HTTPException(status_code=500, detail="크롤링 결과 없음")

    try:
        result = extract_with_ai(posting, site)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 추출 실패: {e}")

    return result
