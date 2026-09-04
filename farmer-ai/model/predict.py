"""
Phase 1 (test step): run a single-image prediction from the command line.

Usage:
    python model/predict.py path/to/leaf.jpg
"""

import sys
from pathlib import Path

import torch
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms
from torchvision.models import mobilenet_v3_small

THIS_DIR = Path(__file__).resolve().parent
MODEL_PATH = THIS_DIR / "model.pt"
IMG_SIZE = 224

_transform = transforms.Compose(
    [
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)

_model = None
_classes = None
_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load_model():
    """Loads the model once and caches it. Safe to call repeatedly (e.g. from FastAPI)."""
    global _model, _classes
    if _model is not None:
        return _model, _classes

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"{MODEL_PATH} not found. Train the model first with: python model/train.py"
        )

    checkpoint = torch.load(MODEL_PATH, map_location=_device)
    classes = checkpoint["classes"]

    model = mobilenet_v3_small(weights=None)
    in_features = model.classifier[-1].in_features
    model.classifier[-1] = torch.nn.Linear(in_features, len(classes))
    model.load_state_dict(checkpoint["model_state"])
    model.to(_device)
    model.eval()

    _model, _classes = model, classes
    return model, classes


def predict_image(image: Image.Image, top_k: int = 3):
    """
    Runs inference on a PIL image.

    Returns:
        {
            "predicted_class": str,
            "confidence": float (0-1),
            "top_k": [{"class": str, "confidence": float}, ...]
        }
    """
    model, classes = load_model()

    image = image.convert("RGB")
    tensor = _transform(image).unsqueeze(0).to(_device)

    with torch.no_grad():
        logits = model(tensor)
        probs = F.softmax(logits, dim=1)[0]

    top_probs, top_idxs = torch.topk(probs, k=min(top_k, len(classes)))

    results = [
        {"class": classes[idx.item()], "confidence": round(prob.item(), 4)}
        for prob, idx in zip(top_probs, top_idxs)
    ]

    return {
        "predicted_class": results[0]["class"],
        "confidence": results[0]["confidence"],
        "top_k": results,
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python model/predict.py path/to/image.jpg")
        sys.exit(1)

    img_path = sys.argv[1]
    img = Image.open(img_path)
    result = predict_image(img)

    print(f"\nImage: {img_path}")
    print(f"Predicted: {result['predicted_class']}  (confidence: {result['confidence']:.2%})")
    print("\nTop predictions:")
    for r in result["top_k"]:
        print(f"  {r['class']:45s} {r['confidence']:.2%}")
