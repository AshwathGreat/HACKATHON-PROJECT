"""
Deterministic government-scheme matching engine.

CRITICAL RULE: this module must NEVER call an LLM and must NEVER invent a
scheme, condition, or eligibility outcome. It only filters
backend/data/schemes.json using plain Python logic, and every result is
phrased as "potentially relevant" / "you may be eligible" - never a guarantee.
"""

import json
from pathlib import Path
from typing import Optional

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "schemes.json"

_cache = None


def _load():
    global _cache
    if _cache is None:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache


def find_potentially_relevant_schemes(
    state: str,
    crop: str,
    district: Optional[str] = None,
    has_insurance: Optional[bool] = None,
    damage_pct: Optional[float] = None,
    farmer_category: Optional[str] = None,
) -> list:
    """
    Pure rule-based filter. Returns a list of scheme dicts the farmer
    *may* be eligible for, each carrying its official_source.

    This is intentionally simple for the MVP: state match + crop match
    (or crop == "*" wildcard). Extend conditions as your scheme database grows,
    but keep every rule explicit and traceable - no fuzzy/LLM matching here.
    """
    schemes = _load()["schemes"]
    matches = []

    state_norm = (state or "").strip().lower()
    crop_norm = (crop or "").strip().lower()

    for scheme in schemes:
        scheme_state = scheme["state"].lower()

        state_ok = (
            "all india" in scheme_state
            or state_norm in scheme_state
            or scheme_state in state_norm
        )
        if not state_ok:
            continue

        applicable_crops = [c.lower() for c in scheme["applicable_crops"]]
        crop_ok = "*" in applicable_crops or crop_norm in applicable_crops
        if not crop_ok:
            continue

        # Scheme-specific extra rule: PMFBY needs a loss event that occurred
        # AFTER enrollment - flag this clearly rather than silently including it.
        note = None
        if scheme["scheme_id"] == "pmfby" and has_insurance is False:
            note = (
                "You indicated you are not currently insured under PMFBY. "
                "This scheme cannot cover a loss that already happened without prior "
                "enrollment, but you may be able to enroll before the next season."
            )

        matches.append({**scheme, "match_note": note})

    return matches
