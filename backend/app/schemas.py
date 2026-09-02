from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, computed_field

from app.scoring.confidence import ConfidenceLabel, confidence_label

Momentum = Literal["Rising", "Surging", "Stable"]


class ConfidenceLabelled(BaseModel):
    """Derives the displayed label from the score so the two cannot drift apart."""

    confidenceScore: int = Field(ge=0, le=100)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def confidenceLabel(self) -> ConfidenceLabel:
        return confidence_label(self.confidenceScore)


class Evidence(BaseModel):
    query: str
    excerpt: str
    platform: str
    observedAt: date
    region: str
    sourceUrl: HttpUrl


class Opportunity(ConfidenceLabelled):
    id: str
    title: str
    region: str
    category: str
    momentum: Momentum
    marketScore: int = Field(ge=0, le=100)
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


class OpportunitySummary(ConfidenceLabelled):
    id: str
    title: str
    region: str
    category: str
    momentum: Momentum
    marketScore: int
    oneLineSummary: str
    whyNow: str

    @classmethod
    def from_opportunity(cls, item: Opportunity) -> "OpportunitySummary":
        return cls(**item.model_dump(include=set(cls.model_fields)))
