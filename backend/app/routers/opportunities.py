from fastapi import APIRouter, HTTPException

from app.schemas import Opportunity, OpportunitySummary
from app.services.opportunities import get_opportunity, list_opportunities

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])


@router.get("", response_model=list[OpportunitySummary])
def list_opportunity_feed() -> list[OpportunitySummary]:
    return list_opportunities()


@router.get("/{opportunity_id}", response_model=Opportunity)
def get_opportunity_detail(opportunity_id: str) -> Opportunity:
    item = get_opportunity(opportunity_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return item
