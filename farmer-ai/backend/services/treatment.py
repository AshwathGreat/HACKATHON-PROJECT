"""
Looks up curated, source-backed guidance for a predicted disease class.
This module NEVER generates agricultural advice itself - it only reads
backend/data/diseases.json. If an LLM is used elsewhere to phrase this
more naturally for a farmer (e.g. for voice output), it must be given
ONLY this data as context and instructed not to add anything beyond it.
"""

import json
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "diseases.json"

_cache = None


def _load():
    global _cache
    if _cache is None:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache


def get_guidance(raw_class: str) -> dict:
    """
    Returns the knowledge-base entry for a given raw class label
    (e.g. 'Tomato___Early_blight'), or a safe fallback if not found.
    """
    kb = _load()
    entry = kb.get(raw_class)

    if entry is None:
        return {
            "crop": "Unknown",
            "disease": raw_class,
            "symptoms": None,
            "immediate_actions": [
                "This condition isn't in our verified knowledge base yet."
            ],
            "prevention": [],
            "warning": "Please consult your local Krishi Vibhag / Krishi Vigyan Kendra "
                       "for expert verification of this crop condition.",
            "source": None,
            "last_verified": None,
        }

    return entry
