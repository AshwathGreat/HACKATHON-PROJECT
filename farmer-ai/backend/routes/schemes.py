from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from services.scheme_engine import find_potentially_relevant_schemes

router = APIRouter()


class SchemeQuery(BaseModel):
    state: str = "Maharashtra"
    crop: str
    district: Optional[str] = None
    has_insurance: Optional[bool] = None
    damage_pct: Optional[float] = None
    farmer_category: Optional[str] = None


@router.post("/schemes/match")
async def match_schemes(query: SchemeQuery):
    """
    Phase 7 endpoint: deterministic scheme matching.
    Always returns results phrased as "potentially relevant" - never a guarantee.
    """
    matches = find_potentially_relevant_schemes(
        state=query.state,
        crop=query.crop,
        district=query.district,
        has_insurance=query.has_insurance,
        damage_pct=query.damage_pct,
        farmer_category=query.farmer_category,
    )

    return {
        "disclaimer": (
            "These are potentially relevant schemes based on the information you gave. "
            "This is not a guarantee of eligibility or approval — please confirm "
            "final eligibility and required documents with the official source or "
            "your local Krishi Vibhag / bank / CSC."
        ),
        "count": len(matches),
        "schemes": matches,
    }
