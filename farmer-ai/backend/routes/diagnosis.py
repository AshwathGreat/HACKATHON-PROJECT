from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from PIL import Image
import io

from services.disease_model import diagnose_image
from services.treatment import get_guidance
from services.i18n import get_all_strings, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

router = APIRouter()


@router.post("/diagnose")
async def diagnose(
    file: UploadFile = File(...),
    language: str = Form(DEFAULT_LANGUAGE)
):
    """
    IMAGE → DISEASE + CONFIDENCE → ACTION GUIDANCE

    When language is hi/mr/ta, symptoms/actions/prevention/warning are
    returned in that language (from diseases_i18n.json).
    Disease name, source stay in English (citation/technical content).
    """
    language = language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    labels   = get_all_strings(language)

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload an image file.")

    try:
        contents = await file.read()
        image    = Image.open(io.BytesIO(contents))
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read the uploaded image.")

    diagnosis = diagnose_image(image)

    if diagnosis["low_confidence"]:
        # Use localized low-confidence message from i18n
        msg = labels.get(
            "low_conf_msg",
            "I'm not confident enough about this diagnosis. "
            "Could you send a clearer, closer photo of the affected leaf in good light? "
            "If the problem is serious, please show the plant to your local "
            "Krishi Vibhag / KVK officer for expert verification."
        )
        return {
            "crop":           diagnosis["crop"],
            "disease":        None,
            "confidence":     diagnosis["confidence"],
            "low_confidence": True,
            "message":        msg,
            "top_k":          diagnosis["top_k"],
            "labels":         labels,
        }

    # Pass language so treatment.py can return translated content
    guidance = get_guidance(diagnosis["raw_class"], language=language)

    return {
        "crop":              diagnosis["crop"],
        "disease":           guidance["disease"],       # always English (disease name)
        "confidence":        diagnosis["confidence"],
        "low_confidence":    False,
        "symptoms":          guidance["symptoms"],
        "immediate_actions": guidance["immediate_actions"],
        "prevention":        guidance["prevention"],
        "warning":           guidance["warning"],
        "source":            guidance["source"],        # always English (citation)
        "top_k":             diagnosis["top_k"],
        "labels":            labels,
    }
