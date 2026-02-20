from fastapi import APIRouter
from match_ai.schemas.schemas import MatchRequest, MatchResponse
from match_ai.services.service import analyze_match

router = APIRouter()


@router.post("/match", response_model=MatchResponse, response_model_exclude_none=True)
async def match(req: MatchRequest) -> MatchResponse:
    return await analyze_match(req.fileUrl, req.jobInfo)