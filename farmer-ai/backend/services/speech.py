"""
PHASE 6 STUB - not yet implemented.

This will hold:
  - speech_to_text(audio_bytes, language_hint=None) -> str
  - text_to_speech(text, language_code) -> bytes (audio)

Planned approach (see README Phase 6):
  - STT: OpenAI Whisper (local, multilingual, works well for Hindi/Marathi)
  - TTS: gTTS or an Indic-language TTS service

Left as a stub in Phase 1-3 so the project structure matches the final
architecture from day one, without forcing you to install Whisper before
you even have a working model + webhook.
"""


def speech_to_text(audio_bytes: bytes, language_hint: str = None) -> str:
    raise NotImplementedError("Implement in Phase 6 - see README.md")


def text_to_speech(text: str, language_code: str) -> bytes:
    raise NotImplementedError("Implement in Phase 6 - see README.md")
