"""
Looks up curated, source-backed guidance for a predicted disease class.
Returns content in the requested language if a translation exists in
diseases_i18n.json, otherwise falls back to English from diseases.json.

Disease name, source, and last_verified always stay in English
(technical/citation content that must not be mistranslated).
"""

import json
from pathlib import Path

_BASE_PATH  = Path(__file__).resolve().parents[1] / "data" / "diseases.json"
_I18N_PATH  = Path(__file__).resolve().parents[1] / "data" / "diseases_i18n.json"

_base_cache = None
_i18n_cache = None


def _load_base():
    global _base_cache
    if _base_cache is None:
        with open(_BASE_PATH, "r", encoding="utf-8") as f:
            _base_cache = json.load(f)
    return _base_cache


def _load_i18n():
    global _i18n_cache
    if _i18n_cache is None:
        with open(_I18N_PATH, "r", encoding="utf-8") as f:
            _i18n_cache = json.load(f)
    return _i18n_cache


def get_guidance(raw_class: str, language: str = "en") -> dict:
    """
    Returns knowledge-base entry for a disease class label
    (e.g. 'Tomato___Early_blight'), translated if possible.

    Fields translated when language != 'en' and translation exists:
        symptoms, immediate_actions, prevention, warning

    Fields always kept in English:
        disease (name), source, last_verified, crop
    """
    base = _load_base()
    entry = base.get(raw_class)

    if entry is None:
        return {
            "crop": "Unknown",
            "disease": raw_class,
            "symptoms": None,
            "immediate_actions": [
                "This condition isn't in our verified knowledge base yet."
            ],
            "prevention": [],
            "warning": (
                "Please consult your local Krishi Vibhag / Krishi Vigyan Kendra "
                "for expert verification of this crop condition."
            ),
            "source": None,
            "last_verified": None,
        }

    # Start with the English base
    result = dict(entry)

    # Overlay translated fields if language is not English
    if language != "en":
        i18n = _load_i18n()
        disease_translations = i18n.get(raw_class, {})
        lang_data = disease_translations.get(language, {})

        if lang_data:
            # Only overlay fields that are translated; keep English for the rest
            for field in ("symptoms", "immediate_actions", "prevention", "warning"):
                if field in lang_data and lang_data[field]:
                    result[field] = lang_data[field]

    return result
