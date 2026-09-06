"""
Automated Kaggle PlantVillage Dataset Downloader & Splitter.
Uses the emmarex/plantdisease dataset on Kaggle (PlantVillage mirror).

Usage:
    python model/kaggle_dataset.py
"""

import os
import shutil
import random
import zipfile
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
SAMPLE_DATA = PROJECT_ROOT / "Ashwath_repo" / "HACKATHON-PROJECT-main" / "SAMPLE DATA"

# Setup Kaggle credentials
kaggle_json_src = SAMPLE_DATA / "kaggle.json"
user_kaggle_dir = Path.home() / ".kaggle"
user_kaggle_file = user_kaggle_dir / "kaggle.json"

if kaggle_json_src.exists() and not user_kaggle_file.exists():
    user_kaggle_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(kaggle_json_src, user_kaggle_file)
    print(f"Copied {kaggle_json_src} -> {user_kaggle_file}")

CLASSES = [
    "Tomato___healthy",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites_Two_spotted_spider_mite",
    "Tomato___Tomato_mosaic_virus",
]

DEST = THIS_DIR / "data"
VAL_SPLIT = 0.2
random.seed(42)


def download_and_prepare():
    print("=== Kaggle PlantVillage Dataset Setup ===")
    print("Dataset slug: emmarex/plantdisease")
    
    # Download via Kaggle CLI / API
    import subprocess
    cmd = ["kaggle", "datasets", "download", "-d", "emmarex/plantdisease", "-p", str(THIS_DIR)]
    print("Running:", " ".join(cmd))
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("Note: To download directly with the Kaggle CLI, ensure your kaggle.json token is configured with valid credentials.")
        print("Error output:", res.stderr)
        return

    zip_file = THIS_DIR / "plantdisease.zip"
    if zip_file.exists():
        raw_dir = THIS_DIR / "plantvillage_raw"
        print(f"Unzipping {zip_file} to {raw_dir}...")
        with zipfile.ZipFile(zip_file, "r") as z:
            z.extractall(raw_dir)

        # Split 7 tomato classes
        for cls in CLASSES:
            matches = list(raw_dir.rglob(cls))
            if not matches:
                print(f"Warning: class folder {cls} not found.")
                continue
            src_dir = matches[0]
            images = list(src_dir.glob("*.*"))
            random.shuffle(images)
            split_idx = int(len(images) * (1 - VAL_SPLIT))
            train_imgs, val_imgs = images[:split_idx], images[split_idx:]

            for split_name, imgs in [("train", train_imgs), ("val", val_imgs)]:
                out_dir = DEST / split_name / cls
                out_dir.mkdir(parents=True, exist_ok=True)
                for img in imgs:
                    shutil.copy(img, out_dir / img.name)

            print(f"Class '{cls}': {len(train_imgs)} train, {len(val_imgs)} val")
        print(f"Dataset successfully prepared in: {DEST}")


if __name__ == "__main__":
    download_and_prepare()
