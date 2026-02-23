from typing import Optional
from pydantic import BaseModel


class ExtractRequest(BaseModel):
    url: str


class JobCardResponse(BaseModel):
    jobTitle: Optional[str]
    companyName: Optional[str]
    employmentType: Optional[str]
    roleText: Optional[str]
    necessaryStack: Optional[list]
    preferStack: Optional[list]
    experienceLevel: Optional[str]
    salaryText: Optional[str]
    workDay: Optional[str]
    locationText: Optional[str]
    deadlineAt: Optional[str]
