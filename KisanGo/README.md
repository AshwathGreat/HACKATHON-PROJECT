# 🌿 KisanGo - WhatsApp Crop Disease Detection & Scheme Advisory Bot

> **A zero-hallucination, multilingual WhatsApp assistant for farmers powered by PyTorch MobileNetV3 (trained on Kaggle PlantVillage) and verified government agricultural databases.**

---

## 🎯 Key Capabilities
1. **Accurate Disease Detection**: Farmer snaps and sends a photo of an affected leaf on WhatsApp. The local PyTorch MobileNetV3-Small model detects the disease with high confidence and zero reliance on external LLMs.
2. **Verified Agricultural Knowledge Base**: Guidance is retrieved deterministically from `data/diseases.json`:
   - Curated symptoms & visual signs
   - Immediate cultural and organic actions
   - Future preventive measures
   - Official citations & extension service sources (UC IPM, Cornell Extension, ICAR, KVK)
3. **Government Scheme Matching**: Queries `data/schemes.json` for potentially relevant government schemes:
   - **PMFBY** (Pradhan Mantri Fasal Bima Yojana - Crop Insurance)
   - **PM-KISAN** (Income support)
   - **MahaDBT** (Maharashtra state farmer subsidy portal)
   - **Krishi Vibhag** (Local disaster relief and advisory)
4. **Multilingual WhatsApp Support**:
   - Supports **English**, **Hindi (हिंदी)**, and **Marathi (मराठी)**.
   - Farmers can reply with *"Hindi"* or *"Marathi"* at any time to switch languages.
5. **WhatsApp Gateway**:
   - **Meta WhatsApp Cloud API**: `GET /webhook` (verification) + `POST /webhook` (messages)

---

## 🏗️ Project Architecture

```
crop/
├── app.py                     <- FastAPI server & WhatsApp webhooks
├── detector.py                <- Core diagnostic & follow-up pipeline
├── models.py                  <- Pydantic schemas (CropDiagnosis, TreatmentPlan)
├── session_store.py           <- Multi-turn session memory per WhatsApp number
│
├── model/                     <- PyTorch CV Model
│   ├── model.pt               <- Pre-trained MobileNetV3 weights (99.5% val acc)
│   ├── predict.py             <- Inference script
│   ├── train.py               <- Training pipeline
│   └── kaggle_dataset.py      <- Kaggle PlantVillage downloader & splitter
│
├── data/                      <- Verified Agricultural Database
│   ├── diseases.json          <- Source-backed disease pathology & remedies
│   ├── schemes.json           <- Government schemes & eligibility rules
│   └── treatments.json        <- Structured treatment database
│
├── services/                  <- Backend Services
│   ├── disease_model.py       <- Model inference wrapper & confidence gate
│   ├── treatment.py           <- Curated advice retrieval
│   └── scheme_engine.py       <- Deterministic scheme matching engine
│
├── static/                    <- Web presentation simulator
│   ├── index.html
│   ├── app.js
│   └── style.css
│
└── sample_images/             <- Test images for instant verification
```

---

## 🚀 Quick Start Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Verify Inference via CLI
Test diagnosis immediately on a sample image:
```bash
python test_cli.py --image sample_images/tomato_early_blight.jpg
```
For Hindi or Marathi:
```bash
python test_cli.py --image sample_images/tomato_early_blight.jpg --lang hi
python test_cli.py --image sample_images/tomato_early_blight.jpg --lang mr
```

### 3. Start the FastAPI Server
```bash
uvicorn app:app --reload --port 8000
```
- Web Simulator: **`http://localhost:8000/`**
- Health Check: **`http://localhost:8000/health`**
- Swagger Docs: **`http://localhost:8000/docs`**

---

## 📱 WhatsApp Webhook Configuration

### Meta WhatsApp Cloud API
1. In Meta Developer Portal > WhatsApp > Configuration:
   - Callback URL: `https://<your-ngrok-domain>.ngrok-free.app/webhook`
   - Verify Token: `agridoc_verify_token` (matches `.env`)
2. Subscribe to `messages` event.

---

## 📊 Kaggle PlantVillage Dataset Integration

The model checkpoint `model/model.pt` comes pre-trained on the Kaggle PlantVillage dataset with 99.5% validation accuracy across 7 tomato classes.

To download the full raw dataset from Kaggle for retraining or inspection:
```bash
python model/kaggle_dataset.py
```
This automatically:
1. Uses your Kaggle credentials (`~/.kaggle/kaggle.json`).
2. Downloads `emmarex/plantdisease`.
3. Extracts and splits 7 classes (80% train / 20% val) into `model/data/`.
4. Allows running `python model/train.py --epochs 10` if retraining is desired.
