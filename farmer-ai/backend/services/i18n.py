"""
Localization for FIXED UI strings only (questions, labels, disclaimers).

IMPORTANT: this module does NOT translate disease guidance or scheme
descriptions - that content stays as-is (English/official source) for
MVP, because auto-translating agricultural/eligibility facts risks
introducing errors. Dynamic content translation is planned for Phase 6
(translation.py) using a proper translation service, ideally reviewed
by a native speaker before farmer-facing use.
"""

import json
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "i18n.json"
SUPPORTED_LANGUAGES = ["en", "hi", "mr", "ta"]
DEFAULT_LANGUAGE = "en"

_cache = None


def _load():
    global _cache
    if _cache is None:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache


def get_string(key: str, language: str = DEFAULT_LANGUAGE) -> str:
    strings = _load()
    lang = language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    return strings.get(lang, {}).get(key) or strings[DEFAULT_LANGUAGE].get(key, key)


def get_all_strings(language: str = DEFAULT_LANGUAGE) -> dict:
    strings = _load()
    lang = language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    return strings.get(lang, strings[DEFAULT_LANGUAGE])
