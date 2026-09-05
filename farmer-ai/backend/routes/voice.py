"""
Phase 6 - Voice API routes.

POST /voice/transcribe  →  { "text": "...", "language": "hi" }
POST /voice/speak       →  MP3 audio bytes (Content-Type: audio/mpeg)
"""

import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from services.speech import speech_to_text, text_to_speech
from services.i18n import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str = Form(DEFAULT_LANGUAGE),
):
    """Farmer speaks → text back. Browser sends WebM audio by default."""
    if language not in SUPPORTED_LANGUAGES:
        language = DEFAULT_LANGUAGE

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio received.")

    try:
        text = speech_to_text(audio_bytes, language_hint=language)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Transcription error")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")

    return {"text": text, "language": language}


class SpeakRequest(BaseModel):
    text: str
    language: str = DEFAULT_LANGUAGE


@router.post("/speak")
async def speak(body: SpeakRequest):
    """Text → MP3 audio. Used to read diagnosis/scheme results aloud."""
    language = body.language if body.language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text is empty.")

    try:
        audio_bytes = text_to_speech(body.text.strip(), language_code=language)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("TTS error")
        raise HTTPException(status_code=500, detail=f"TTS failed: {e}")

    return Response(content=audio_bytes, media_type="audio/mpeg")
