"""
Phase 6 - Voice pipeline implementation.

speech_to_text  : audio bytes  -> transcribed text   (Whisper, local, no API key)
text_to_speech  : text + lang  -> MP3 audio bytes     (gTTS, free, needs internet)

Language codes: en | hi | mr | ta  (same across our app, Whisper, and gTTS)

Install requirements:
    pip install openai-whisper gtts ffmpeg-python
    # Also need ffmpeg on PATH — see README
"""

import io
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

_whisper_model = None


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        try:
            import whisper
            # "base" = ~74 MB, good for Hindi/Marathi/Tamil on CPU.
            # Change to "small" for better accuracy if you have a GPU.
            _whisper_model = whisper.load_model("base")
            logger.info("Whisper 'base' model loaded.")
        except ImportError:
            raise RuntimeError(
                "openai-whisper is not installed. Run:  pip install openai-whisper"
            )
    return _whisper_model


_LANG_MAP = {"en": "en", "hi": "hi", "mr": "mr", "ta": "ta"}


def speech_to_text(audio_bytes: bytes, language_hint: str = None) -> str:
    """
    Convert audio bytes (webm/ogg/wav/mp3) to text using Whisper locally.
    No API key needed. First call downloads the model (~74 MB, one-time).
    """
    model = _get_whisper()
    lang = _LANG_MAP.get(language_hint) if language_hint else None

    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        options = {}
        if lang:
            options["language"] = lang
        result = model.transcribe(tmp_path, **options)
        text = result["text"].strip()
        logger.info("Whisper transcribed (%s): %r", lang or "auto", text[:80])
        return text
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def text_to_speech(text: str, language_code: str = "en") -> bytes:
    """
    Convert text to MP3 bytes using gTTS (Google Text-to-Speech).
    Needs internet. Supports en, hi, mr, ta.
    """
    try:
        from gtts import gTTS
    except ImportError:
        raise RuntimeError("gTTS is not installed. Run:  pip install gtts")

    lang = _LANG_MAP.get(language_code, "en")
    buf = io.BytesIO()
    gTTS(text=text, lang=lang, slow=False).write_to_fp(buf)
    buf.seek(0)
    audio_bytes = buf.read()
    logger.info("gTTS generated %d bytes, lang=%s", len(audio_bytes), lang)
    return audio_bytes
