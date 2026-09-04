"""
Wraps model/predict.py so the FastAPI layer never talks to PyTorch directly.
Responsible for:
  - running inference
  - splitting the raw PlantVillage class label into crop + disease
  - applying the low-confidence rule (ask for a clearer photo / recommend expert)
"""

import os
import sys
from pathlib import Path

from PIL import Image

# Make model/ importable from backend/
MODEL_DIR = Path(__file__).resolve().parents[2] / "model"
sys.path.insert(0, str(MODEL_DIR))

from predict import predict_image  # noqa: E402  (import after sys.path tweak)

CONFIDENCE_THRESHOLD = float(os.getenv("MODEL_CONFIDENCE_THRESHOLD", "0.55"))


def _split_class_label(raw_label: str):
    """
    PlantVillage-style labels look like 'Tomato___Early_blight'.
    Returns (crop, disease_key) where disease_key matches diseases.json keys exactly.
    """
    return raw_label, raw_label  # disease_key == raw_label; crop parsed separately below


def diagnose_image(image: Image.Image) -> dict:
    """
    Returns a dict ready to hand to the knowledge base lookup:
        {
            "raw_class": "Tomato___Early_blight",
            "crop": "Tomato",
            "confidence": 0.87,
            "top_k": [...],
            "low_confidence": False
        }
    """
    result = predict_image(image, top_k=3)
    raw_class = result["predicted_class"]
    confidence = result["confidence"]

    crop = raw_class.split("___")[0] if "___" in raw_class else "Unknown"

    return {
        "raw_class": raw_class,
        "crop": crop,
        "confidence": confidence,
        "top_k": result["top_k"],
        "low_confidence": confidence < CONFIDENCE_THRESHOLD,
    }
