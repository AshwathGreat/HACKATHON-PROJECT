from fastapi import APIRouter, UploadFile, File, HTTPException
from PIL import Image
import io

from services.disease_model import diagnose_image
from services.treatment import get_guidance

router = APIRouter()


@router.post("/diagnose")
async def diagnose(file: UploadFile = File(...)):
    """
    Phase 2 core endpoint: IMAGE -> DISEASE + CONFIDENCE -> ACTION GUIDANCE

    Accepts an image upload, runs the CV model, and returns crop, disease,
    confidence, and curated (source-backed) guidance from diseases.json.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload an image file.")

    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read the uploaded image.")

    diagnosis = diagnose_image(image)

    if diagnosis["low_confidence"]:
        return {
            "crop": diagnosis["crop"],
            "disease": None,
            "confidence": diagnosis["confidence"],
            "low_confidence": True,
            "message": (
                "I'm not confident enough about this diagnosis. "
                "Could you send a clearer, closer photo of the affected leaf in good light? "
                "If the problem is serious, please also show the plant to your local "
                "Krishi Vibhag / KVK officer for expert verification."
            ),
            "top_k": diagnosis["top_k"],
        }

    guidance = get_guidance(diagnosis["raw_class"])

    return {
        "crop": diagnosis["crop"],
        "disease": guidance["disease"],
        "confidence": diagnosis["confidence"],
        "low_confidence": False,
        "symptoms": guidance["symptoms"],
        "immediate_actions": guidance["immediate_actions"],
        "prevention": guidance["prevention"],
        "warning": guidance["warning"],
        "source": guidance["source"],
        "top_k": diagnosis["top_k"],
    }
