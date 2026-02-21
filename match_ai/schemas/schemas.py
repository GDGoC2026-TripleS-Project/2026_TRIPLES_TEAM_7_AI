from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel


class JobInfo(BaseModel):
    jobTitle: Optional[str] = None
    companyName: Optional[str] = None
    employmentType: List[str] = []
    roleText: List[str] = []
    necessaryStack: List[str] = []
    preferStack: List[str] = []
    experienceLevel: List[str] = []
    salaryText: Optional[str] = None
    workDay: Optional[str] = None
    locationText: Optional[str] = None
    deadlineAt: Optional[str] = None

class MatchRequest(BaseModel):
    fileUrl: str
    jobInfo: JobInfo


class MatchItem(BaseModel):
    comment: str
    isRequired: Optional[bool] = None

    model_config = {"exclude_none": True}

class MatchResponse(BaseModel):
    matchPercent: int
    strengthTop3: List[MatchItem]
    gapTop3: List[MatchItem]
    riskTop3: List[MatchItem]
