"""
Turns the deterministic scheme_engine.py matcher into a step-by-step
conversation: asks state -> district -> crop -> insurance -> damage ->
category, one question at a time, then returns matches.

Supports PREFILLED answers (e.g. the crop already known from a photo
diagnosis, or the state defaulting to Maharashtra since that's this
project's focus) - prefilled fields are skipped in the conversation
instead of being re-asked.

MVP note: sessions are stored in-memory (a plain dict), so they reset if
the server restarts. That's fine for a demo. For a real deployment,
replace SESSIONS with a proper store (Redis/Postgres) - see README Phase 7.

This module is transport-agnostic: the same session logic will be reused
by the WhatsApp webhook in Phase 5, not just the test webpage.
"""

import uuid
from typing import Optional

from services.i18n import get_string
from services.scheme_engine import find_potentially_relevant_schemes

# Each entry: (answer_key, i18n_question_key)
QUESTION_FLOW = [
    ("state", "ask_state"),
    ("district", "ask_district"),
    ("crop", "ask_crop"),
    ("has_insurance", "ask_insurance"),
    ("damage_pct", "ask_damage"),
    ("farmer_category", "ask_category"),
]

SESSIONS: dict = {}


def _parse_answer(key: str, raw_answer: str):
    """Light parsing for the two non-string fields. Never raises - falls
    back to storing the raw string if parsing fails, so a farmer's
    unexpected phrasing doesn't crash the flow."""
    text = raw_answer.strip()

    if key == "has_insurance":
        lower = text.lower()
        if lower in ("yes", "y", "haan", "हाँ", "हो", "ஆம்"):
            return True
        if lower in ("no", "n", "nahi", "नहीं", "नाही", "இல்லை"):
            return False
        return None  # unknown -> treated as "not stated" by scheme_engine

    if key == "damage_pct":
        digits = "".join(ch for ch in text if ch.isdigit())
        return float(digits) if digits else None

    if key == "farmer_category":
        if text.lower() == "skip":
            return None
        return text

    return text


def _finalize(session_id: str) -> dict:
    session = SESSIONS.pop(session_id)  # one-shot flow for MVP; free the memory
    language = session["language"]
    answers = session["answers"]

    matches = find_potentially_relevant_schemes(
        state=answers.get("state") or "Maharashtra",
        crop=answers.get("crop") or "",
        district=answers.get("district"),
        has_insurance=answers.get("has_insurance"),
        damage_pct=answers.get("damage_pct"),
        farmer_category=answers.get("farmer_category"),
    )

    return {
        "session_id": session_id,
        "done": True,
        "disclaimer": get_string("disclaimer", language),
        "no_matches_message": get_string("no_matches", language) if not matches else None,
        "count": len(matches),
        "schemes": matches,
        "answers_given": answers,
    }


def start_session(language: str = "en", prefill: Optional[dict] = None) -> dict:
    """
    prefill: e.g. {"crop": "Tomato", "state": "Maharashtra"} - these
    fields are stored immediately and skipped in the question flow.
    """
    prefill = {k: v for k, v in (prefill or {}).items() if v not in (None, "")}

    session_id = str(uuid.uuid4())
    remaining_flow = [(k, q) for k, q in QUESTION_FLOW if k not in prefill]

    SESSIONS[session_id] = {
        "language": language,
        "flow": remaining_flow,
        "step": 0,
        "answers": dict(prefill),
    }

    if not remaining_flow:
        # Everything was prefilled (unlikely, but handle gracefully) -> resolve immediately
        return _finalize(session_id)

    first_key, first_q_key = remaining_flow[0]
    return {
        "session_id": session_id,
        "done": False,
        "question": get_string(first_q_key, language),
        "field": first_key,
    }


def answer_session(session_id: str, answer: str) -> dict:
    session = SESSIONS.get(session_id)
    if session is None:
        return {"error": "Session not found or expired. Please start again."}

    language = session["language"]
    flow = session["flow"]
    step = session["step"]
    current_key, _ = flow[step]

    session["answers"][current_key] = _parse_answer(current_key, answer)
    session["step"] += 1

    if session["step"] < len(flow):
        next_key, next_q_key = flow[session["step"]]
        return {
            "session_id": session_id,
            "done": False,
            "question": get_string(next_q_key, language),
            "field": next_key,
        }

    return _finalize(session_id)
