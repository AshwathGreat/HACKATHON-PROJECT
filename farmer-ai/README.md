# Farmer AI Assistant — SIH 2026 (Govt. of Maharashtra)

Voice-first, multilingual WhatsApp agricultural assistant:
**IDENTIFY → ACT → RECOVER**

This README is the working tutorial. It currently covers **Phase 1–3**
(dataset → model → `/diagnose` API → simple test webpage) end-to-end,
which is the part you can build and demo *today*, without any WhatsApp
account or Meta approval. Phases 4–8 are scoped at the bottom so you know
exactly what's coming next — we'll build those the same way, step by step.

> ⚠️ **Where to run this**: this project needs internet access (to
> download the dataset and pip-install packages) and ideally a GPU for
> training. Run it on your own laptop, or on **Google Colab** (free GPU) —
> not in a sandboxed environment without internet.

---

## 0. Prerequisites

- Python 3.10 or 3.11
- ~3–5 GB free disk space (dataset + model)
- A Kaggle account (for downloading PlantVillage) — free
- (Optional but recommended) an NVIDIA GPU, or use Google Colab's free GPU

---

## 1. Project setup

```bash
git clone <your-repo>   # or just use this folder
cd farmer-ai

python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env           # fill in values later, as you need them
```

---

## PHASE 1 — Dataset → Tomato Model → Test Predictions

### 1.1 Get the PlantVillage dataset

The PlantVillage dataset is on Kaggle. Easiest path:

1. Create a free Kaggle account: https://www.kaggle.com
2. Get an API token: Kaggle → your profile → **Settings** → **Create New Token**
   (downloads `kaggle.json`)
3. Install the Kaggle CLI and download:

```bash
pip install kaggle
mkdir -p ~/.kaggle && mv kaggle.json ~/.kaggle/ && chmod 600 ~/.kaggle/kaggle.json

# This is the most commonly used PlantVillage mirror on Kaggle:
kaggle datasets download -d emmarex/plantdisease
unzip plantdisease.zip -d plantvillage_raw
```

(If that exact dataset slug has changed, just search "PlantVillage" on
Kaggle — several mirrors exist with the same folder structure:
`Species___Disease/` subfolders full of leaf images.)

### 1.2 Keep only the Tomato classes, and split train/val

We only want these 7 tomato classes for the MVP:

```
Tomato___healthy
Tomato___Early_blight
Tomato___Late_blight
Tomato___Leaf_Mold
Tomato___Septoria_leaf_spot
Tomato___Spider_mites_Two_spotted_spider_mite
Tomato___Tomato_mosaic_virus
```

Run this one-off script to filter + split (80% train / 20% val) into the
layout `train.py` expects:

```bash
python3 - <<'EOF'
import shutil, random
from pathlib import Path

SRC = Path("plantvillage_raw")  # adjust if your unzip nested it differently
DEST = Path("model/data")
CLASSES = [
    "Tomato___healthy",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites_Two_spotted_spider_mite",
    "Tomato___Tomato_mosaic_virus",
]
VAL_SPLIT = 0.2
random.seed(42)

# find the source folders (search recursively in case of nested zip folders)
def find_class_dir(cls):
    matches = list(SRC.rglob(cls))
    return matches[0] if matches else None

for cls in CLASSES:
    src_dir = find_class_dir(cls)
    if not src_dir:
        print(f"WARNING: could not find source folder for {cls} - check your unzip path")
        continue

    images = list(src_dir.glob("*.*"))
    random.shuffle(images)
    split_idx = int(len(images) * (1 - VAL_SPLIT))
    train_imgs, val_imgs = images[:split_idx], images[split_idx:]

    for split_name, imgs in [("train", train_imgs), ("val", val_imgs)]:
        out_dir = DEST / split_name / cls
        out_dir.mkdir(parents=True, exist_ok=True)
        for img in imgs:
            shutil.copy(img, out_dir / img.name)

    print(f"{cls}: {len(train_imgs)} train, {len(val_imgs)} val")

print("Done. Check model/data/train and model/data/val")
EOF
```

You should end up with:

```
model/data/train/Tomato___healthy/*.jpg   (and 6 other class folders)
model/data/val/Tomato___healthy/*.jpg     (and 6 other class folders)
```

### 1.3 Train the model

```bash
python model/train.py --epochs 10 --batch-size 32
```

What this does (see `model/train.py`):
- Loads **MobileNetV3-Small** pretrained on ImageNet
- Freezes the backbone, trains only a new classification head for the
  first `--unfreeze-at-epoch` epochs (fast, avoids overfitting on a
  moderate dataset)
- Then unfreezes the whole network and fine-tunes at a lower learning rate
- Saves the **best** validation-accuracy checkpoint to `model/model.pt`
- Writes `model/training_log.json` with per-epoch metrics — use this for
  your report/demo slide. **Report the real val_acc. Never round up.**

On a free Colab GPU, 10 epochs on ~7 tomato classes should take well
under 30 minutes. On CPU it will be much slower (hours) — Colab is
strongly recommended for this step.

### 1.4 Test predictions

```bash
python model/predict.py path/to/some_test_leaf.jpg
```

You should see output like:

```
Predicted: Tomato___Early_blight  (confidence: 91.2%)

Top predictions:
  Tomato___Early_blight                        91.2%
  Tomato___Septoria_leaf_spot                    5.1%
  Tomato___healthy                               2.0%
```

✅ **Phase 1 milestone reached once this works reliably on a handful of
test images you set aside (not used in train/val).**

---

## PHASE 2 — FastAPI `/diagnose` endpoint

The backend code is already built (`backend/main.py`,
`backend/routes/diagnosis.py`, `backend/services/`). It reuses
`model/predict.py` and layers on:
- crop/disease parsing
- the low-confidence fallback rule (asks for a clearer photo instead of
  guessing) — controlled by `MODEL_CONFIDENCE_THRESHOLD` in `.env`
- curated, source-backed guidance from `backend/data/diseases.json`
  (never LLM-generated)

Run it:

```bash
cd backend
uvicorn main:app --reload
```

Test with curl:

```bash
curl -X POST http://localhost:8000/diagnose \
  -F "file=@/path/to/leaf.jpg"
```

Or open the interactive docs at **http://localhost:8000/docs** and try
`/diagnose` from there.

✅ **Phase 2 milestone: `/diagnose` returns crop, disease, confidence, and
curated action guidance with a source.**

---

## PHASE 3 — Simple test webpage

Already built at `backend/static/index.html`, served automatically at
**http://localhost:8000/** by the same FastAPI app (no separate server
needed). Upload an image, click Diagnose, see the result rendered.

This is your **demo fallback** if the WhatsApp integration has any hiccup
during judging — you can show the exact same pipeline working live.

---

## What's already scaffolded for later phases

So the project structure matches the final architecture from day one,
these files already exist but are intentionally **stubs / not wired into
`main.py` yet**:

- `backend/routes/whatsapp.py` — Phase 4/5
- `backend/routes/voice.py`, `backend/services/speech.py`,
  `backend/services/translation.py` — Phase 6
- `backend/data/schemes.json` + `backend/services/scheme_engine.py` +
  `backend/routes/schemes.py` — **this one is already functional!** You
  can test it right now:

```bash
curl -X POST http://localhost:8000/schemes/match \
  -H "Content-Type: application/json" \
  -d '{"state": "Maharashtra", "crop": "Tomato", "has_insurance": false}'
```

It deterministically matches against 4 real, sourced schemes (PMFBY,
PM-KISAN, MahaDBT Maharashtra portal, Maharashtra Dept. of Agriculture) —
no LLM involved, every result carries `official_source` and the response
always includes the "potentially relevant, not a guarantee" disclaimer.
This gets fully wired into the conversation flow in Phase 7.

---

## Roadmap: Phases 4–8 (we'll build these next, same step-by-step way)

**Phase 4 — Meta WhatsApp Cloud API + webhook**
Create a Meta developer app, get a test WhatsApp number, implement
`GET /webhook` (verification handshake) and `POST /webhook` (receive
messages) in `backend/routes/whatsapp.py`, expose your local server via
ngrok for testing.

**Phase 5 — WhatsApp image → disease prediction → response**
Wire incoming WhatsApp images into the existing `/diagnose` logic and
send the formatted result back via the Cloud API's send-message endpoint.

**Phase 6 — Voice + multilingual support**
Implement `speech.py` (Whisper for speech-to-text) and `translation.py`
(language detection + localizing the *verified* diagnosis/scheme text —
never generating new facts), prioritizing Marathi + Hindi + English for
MVP.

**Phase 7 — Full government scheme conversation flow**
Turn the already-working `/schemes/match` endpoint into a WhatsApp
conversation that asks for state/district/crop/insurance/damage
step-by-step and returns matches.

**Phase 8 — Testing, polish, demo prep, documentation**

---

## Engineering principles this project follows (don't break these)

1. `diseases.json` and `schemes.json` are the single source of truth —
   no LLM ever invents agricultural advice or scheme eligibility.
2. Every scheme result is phrased "potentially relevant" / "you may be
   eligible" — never a guarantee.
3. Every disease/scheme entry carries a source.
4. Low-confidence predictions ask for a clearer photo or recommend expert
   verification — they never guess.
5. No pesticide doses are given directly by the system for MVP — it
   points to the local Krishi Vibhag / KVK / licensed dealer.
6. Secrets live in `.env`, never in source code.

---

## Project structure

```
farmer-ai/
├── backend/
│   ├── main.py
│   ├── routes/          diagnosis.py (live) · schemes.py (live) · whatsapp.py, voice.py (stubs)
│   ├── services/        disease_model.py, treatment.py, scheme_engine.py (live)
│   │                    speech.py, translation.py (stubs)
│   ├── data/             diseases.json, schemes.json, treatments.json
│   └── static/index.html
├── model/
│   ├── train.py
│   ├── predict.py
│   └── model.pt          <- created after you train
├── requirements.txt
├── .env.example
└── README.md
```
