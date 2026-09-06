"""
CLI Test Tool for AgriDoctor WhatsApp Bot
Diagnose crop diseases directly from the command line using PyTorch MobileNetV3 and the agricultural database.

Usage:
    python test_cli.py --image sample_images/tomato_early_blight.jpg
    python test_cli.py --image sample_images/tomato_early_blight.jpg --lang hi
    python test_cli.py --image sample_images/tomato_early_blight.jpg --lang mr
"""

import argparse
import mimetypes
import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from detector import diagnose_crop_image, answer_follow_up


def test_cli():
    parser = argparse.ArgumentParser(description="KisanGo Crop Disease Diagnostic CLI")
    parser.add_argument("--image", type=str, help="Path to crop/leaf image file", default="sample_images/tomato_early_blight.jpg")
    parser.add_argument("--caption", type=str, help="Farmer caption or question", default="")
    parser.add_argument("--lang", type=str, help="Language code (en, hi, mr)", default="en")

    args = parser.parse_args()

    print("\n" + "=" * 55)
    print(" 🌾 KisanGo - WhatsApp Bot Diagnostic CLI")
    print(" ⚡ Model: PyTorch MobileNetV3 (PlantVillage Kaggle)")
    print(" 📚 Database: diseases.json + schemes.json (Zero LLM)")
    print("=" * 55 + "\n")

    if not os.path.exists(args.image):
        print(f"[ERROR] Image file not found: {args.image}")
        sys.exit(1)

    mime_type, _ = mimetypes.guess_type(args.image)
    if not mime_type:
        mime_type = "image/jpeg"

    print(f"[INFO] Reading image: {args.image} ({mime_type})")
    with open(args.image, "rb") as f:
        img_bytes = f.read()

    print(f"[INFO] Running inference and database lookup (language: {args.lang})...")
    diagnosis = diagnose_crop_image(
        image_bytes=img_bytes,
        mime_type=mime_type,
        user_caption=args.caption,
        language=args.lang
    )

    print("\n" + "-" * 55)
    print(" 📊 STRUCTURED DIAGNOSIS RESULT")
    print("-" * 55)
    print(f"Crop Name:       {diagnosis.crop_name}")
    print(f"Condition:       {diagnosis.condition_name}")
    print(f"Healthy:         {diagnosis.is_healthy}")
    print(f"Confidence:      {diagnosis.confidence_score * 100:.1f}%")

    print("\n" + "-" * 55)
    print(" 📱 FARMER WHATSAPP FORMATTED MESSAGE")
    print("-" * 55)
    print(diagnosis.farmer_friendly_summary)
    print("-" * 55 + "\n")


if __name__ == "__main__":
    test_cli()
