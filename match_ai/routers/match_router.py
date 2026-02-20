from fastapi import APIRouter
from schemas.schemas import MatchRequest, MatchResponse
from services.service import analyze_match

router = APIRouter()


@router.post("/match", response_model=MatchResponse, response_model_exclude_none=True)
async def match(req: MatchRequest) -> MatchResponse:
    return await analyze_match(req.fileUrl, req.jobInfo)