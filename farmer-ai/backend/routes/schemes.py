from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from services.scheme_engine import find_potentially_relevant_schemes
from services.scheme_conversation import start_session, answer_session
from services.i18n import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

router = APIRouter()


class SchemeQuery(BaseModel):
    state: str = "Maharashtra"
    crop: str
    district: Optional[str] = None
    has_insurance: Optional[bool] = None
    damage_pct: Optional[float] = None
    farmer_category: Optional[str] = None


class StartSessionRequest(BaseModel):
    language: str = DEFAULT_LANGUAGE
    crop: Optional[str] = None       # pre-filled from /diagnose result
    state: str = "Maharashtra"       # pre-filled from state dropdown
    district: Optional[str] = None  # pre-filled from district dropdown — skips that question


class AnswerSessionRequest(BaseModel):
    session_id: str
    answer: str


@router.post("/schemes/session/start")
async def start_scheme_session(req: StartSessionRequest):
    """
    Begin the guided scheme-matching conversation.
    state, district, and crop are passed as prefill so the farmer
    is never asked for something they already selected.
    Remaining questions: insurance status, damage %, farmer category.
    """
    language = req.language if req.language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    prefill = {
        "crop": req.crop,
        "state": req.state,
        "district": req.district,
    }
    return start_session(language, prefill=prefill)


@router.post("/schemes/session/answer")
async def answer_scheme_session(req: AnswerSessionRequest):
    return answer_session(req.session_id, req.answer)


@router.post("/schemes/match")
async def match_schemes(query: SchemeQuery):
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
            "This is not a guarantee of eligibility — please confirm with the official "
            "source or your local Krishi Vibhag / bank / CSC."
        ),
        "count": len(matches),
        "schemes": matches,
    }
