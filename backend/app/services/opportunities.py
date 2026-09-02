from app.demo_data import DEMO_OPPORTUNITIES
from app.schemas import Opportunity, OpportunitySummary


def list_opportunities() -> list[OpportunitySummary]:
    return [OpportunitySummary.from_opportunity(item) for item in DEMO_OPPORTUNITIES]


def get_opportunity(opportunity_id: str) -> Opportunity | None:
    return next((item for item in DEMO_OPPORTUNITIES if item.id == opportunity_id), None)
