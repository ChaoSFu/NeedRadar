from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

Momentum = Literal["Rising", "Surging", "Stable"]


class Evidence(BaseModel):
    query: str
    excerpt: str
    platform: str
    observedAt: date
    region: str
    sourceUrl: HttpUrl


class Opportunity(BaseModel):
    id: str
    title: str
    region: str
    category: str
    momentum: Momentum
    marketScore: int = Field(ge=0, le=100)
    confidenceScore: int = Field(ge=0, le=100)
    oneLineSummary: str
    problem: str
    targetUser: str
    jobToBeDone: str
    painPoints: list[str]
    whyNow: str
    workarounds: list[str]
    aiAngle: str
    possibleMvp: str
    evidence: list[Evidence]


class OpportunitySummary(BaseModel):
    id: str
    title: str
    region: str
    category: str
    momentum: Momentum
    marketScore: int
    confidenceScore: int
    oneLineSummary: str
    whyNow: str

    @classmethod
    def from_opportunity(cls, item: Opportunity) -> "OpportunitySummary":
        return cls(**item.model_dump(include=set(cls.model_fields)))
