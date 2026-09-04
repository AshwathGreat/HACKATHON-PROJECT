"""
PHASE 6 STUB - not yet implemented.

This will hold:
  - detect_language(text) -> language_code
  - localize_response(structured_data, target_language) -> str

IMPORTANT: this module's job is ONLY to translate/phrase verified data
(from treatment.py / scheme_engine.py) naturally in the farmer's language.
It must never be used to generate new agricultural facts or scheme
eligibility claims - those come exclusively from the deterministic
services. If using an LLM here, the prompt must explicitly restrict it
to translating/rephrasing the given structured data.
"""


def detect_language(text: str) -> str:
    raise NotImplementedError("Implement in Phase 6 - see README.md")


def localize_response(structured_data: dict, target_language: str) -> str:
    raise NotImplementedError("Implement in Phase 6 - see README.md")
