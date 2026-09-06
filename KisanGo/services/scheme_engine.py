"""
Deterministic government-scheme matching engine.

CRITICAL RULE: this module must NEVER call an LLM and must NEVER invent a
scheme, condition, or eligibility outcome. It only filters
data/schemes.json using plain Python logic, and every result is
phrased as "potentially relevant" / "you may be eligible" - never a guarantee.
Supports all 28 states of India + Central government schemes.
"""

import json
from pathlib import Path
from typing import Optional

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "schemes.json"

_cache = None

# Comprehensive 28 states normalization dictionary (English aliases, abbreviations, Hindi/Marathi)
STATE_ALIASES = {
    # Andhra Pradesh
    "andhra pradesh": "Andhra Pradesh", "andhra": "Andhra Pradesh", "ap": "Andhra Pradesh", "आंध्र प्रदेश": "Andhra Pradesh",
    # Arunachal Pradesh
    "arunachal pradesh": "Arunachal Pradesh", "arunachal": "Arunachal Pradesh", "ar": "Arunachal Pradesh", "अरुणाचल प्रदेश": "Arunachal Pradesh",
    # Assam
    "assam": "Assam", "as": "Assam", "असम": "Assam", "आसाम": "Assam",
    # Bihar
    "bihar": "Bihar", "br": "Bihar", "बिहार": "Bihar",
    # Chhattisgarh
    "chhattisgarh": "Chhattisgarh", "chhatisgarh": "Chhattisgarh", "cg": "Chhattisgarh", "छत्तीसगढ़": "Chhattisgarh",
    # Goa
    "goa": "Goa", "ga": "Goa", "गोवा": "Goa",
    # Gujarat
    "gujarat": "Gujarat", "gujrat": "Gujarat", "gj": "Gujarat", "गुजरात": "Gujarat",
    # Haryana
    "haryana": "Haryana", "hr": "Haryana", "हरियाणा": "Haryana",
    # Himachal Pradesh
    "himachal pradesh": "Himachal Pradesh", "himachal": "Himachal Pradesh", "hp": "Himachal Pradesh", "हिमाचल प्रदेश": "Himachal Pradesh",
    # Jharkhand
    "jharkhand": "Jharkhand", "jh": "Jharkhand", "झारखंड": "Jharkhand",
    # Karnataka
    "karnataka": "Karnataka", "ka": "Karnataka", "kar": "Karnataka", "कर्नाटक": "Karnataka",
    # Kerala
    "kerala": "Kerala", "kl": "Kerala", "ker": "Kerala", "केरल": "Kerala", "केरळ": "Kerala",
    # Madhya Pradesh
    "madhya pradesh": "Madhya Pradesh", "mp": "Madhya Pradesh", "मध्य प्रदेश": "Madhya Pradesh",
    # Maharashtra
    "maharashtra": "Maharashtra", "maha": "Maharashtra", "mh": "Maharashtra", "महाराष्ट्र": "Maharashtra",
    # Manipur
    "manipur": "Manipur", "mn": "Manipur", "मणिपुर": "Manipur",
    # Meghalaya
    "meghalaya": "Meghalaya", "ml": "Meghalaya", "मेघालय": "Meghalaya",
    # Mizoram
    "mizoram": "Mizoram", "mz": "Mizoram", "मिजोरम": "Mizoram",
    # Nagaland
    "nagaland": "Nagaland", "nl": "Nagaland", "नागालैंड": "Nagaland",
    # Odisha
    "odisha": "Odisha", "orissa": "Odisha", "od": "Odisha", "or": "Odisha", "ओडिशा": "Odisha", "उड़ीसा": "Odisha",
    # Punjab
    "punjab": "Punjab", "pb": "Punjab", "पंजाब": "Punjab",
    # Rajasthan
    "rajasthan": "Rajasthan", "raj": "Rajasthan", "rj": "Rajasthan", "राजस्थान": "Rajasthan",
    # Sikkim
    "sikkim": "Sikkim", "sk": "Sikkim", "सिक्किम": "Sikkim",
    # Tamil Nadu
    "tamil nadu": "Tamil Nadu", "tamilnadu": "Tamil Nadu", "tn": "Tamil Nadu", "तमिलनाडु": "Tamil Nadu", "तमिळनाडू": "Tamil Nadu",
    # Telangana
    "telangana": "Telangana", "ts": "Telangana", "tg": "Telangana", "तेलंगाना": "Telangana",
    # Tripura
    "tripura": "Tripura", "tr": "Tripura", "त्रिपुरा": "Tripura",
    # Uttar Pradesh
    "uttar pradesh": "Uttar Pradesh", "up": "Uttar Pradesh", "उत्तर प्रदेश": "Uttar Pradesh", "उप्र": "Uttar Pradesh",
    # Uttarakhand
    "uttarakhand": "Uttarakhand", "uttaranchal": "Uttarakhand", "uk": "Uttarakhand", "ua": "Uttarakhand", "उत्तराखंड": "Uttarakhand",
    # West Bengal
    "west bengal": "West Bengal", "bengal": "West Bengal", "wb": "West Bengal", "पश्चिम बंगाल": "West Bengal"
}


def normalize_state(state_input: Optional[str]) -> str:
    """Normalizes raw user state input into canonical 28 state name."""
    if not state_input:
        return "Maharashtra"
    clean = state_input.strip().lower()
    return STATE_ALIASES.get(clean, state_input.strip().title())


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
    Pure rule-based filter across all 28 states and Central schemes.
    Returns a list of scheme dicts the farmer may be eligible for.
    """
    schemes = _load()["schemes"]
    matches = []

    canonical_state = normalize_state(state)
    state_norm = canonical_state.lower()
    crop_norm = (crop or "").strip().lower()

    for scheme in schemes:
        scheme_state = scheme.get("state", "").lower()

        # State check: match "All India", "all", or exact state match
        state_ok = (
            "all india" in scheme_state
            or scheme_state == "all"
            or state_norm in scheme_state
            or scheme_state in state_norm
        )
        if not state_ok:
            continue

        # Crop check: match wildcard "*" or specific crop name
        applicable_crops = [c.lower() for c in scheme.get("applicable_crops", ["*"])]
        crop_ok = (
            "*" in applicable_crops
            or not crop_norm
            or crop_norm in applicable_crops
            or any(crop_norm in c or c in crop_norm for c in applicable_crops)
        )
        if not crop_ok:
            continue

        conditions = scheme.get("conditions", {})
        min_damage = conditions.get("min_damage_pct")
        note = None

        if min_damage is not None:
            if damage_pct is None:
                note = (
                    f"This scheme typically requires at least ~{min_damage:.0f}% crop damage. "
                    "You didn't specify a damage percentage, so eligibility depends on damage assessment."
                )
            elif damage_pct < min_damage:
                # Does not meet threshold
                continue

        # Scheme-specific rule: PMFBY needs enrollment before loss
        if scheme["scheme_id"] == "pmfby" and has_insurance is False:
            note = (
                "You indicated you are not currently insured under PMFBY. "
                "PMFBY requires enrollment before a loss event occurs, but you can enroll before the next Kharif/Rabi season."
            )

        matches.append({**scheme, "match_note": note, "matched_state": canonical_state})

    return matches
