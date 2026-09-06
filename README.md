# 🌾 KisanGo — Smart Farming Assistant

> **Voice-first, multilingual AI agricultural assistant for Indian farmers**
> Built for **Smart India Hackathon 2026** · Problem Statement: Govt. of Maharashtra

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.4-EE4C2C?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)

---

## 📌 Problem Statement

140 million+ Indian farmers face three critical barriers when their crops are affected by disease:

1. **No expert access** — Agricultural officers are scarce; farmers rely on guesswork
2. **Language barrier** — Most digital tools work only in English
3. **Scheme ignorance** — Farmers lose crores in unclaimed government compensation every year

KisanGo solves all three in one unified, voice-driven flow.

---

## 🎯 The Solution — IDENTIFY → ACT → RECOVER


---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔬 **AI Disease Detection** | MobileNetV3-Small trained on PlantVillage — identifies 7 tomato diseases |
| 🗣️ **Voice Input** | Farmer speaks in their language — Whisper transcribes locally (no API key) |
| 🔊 **Voice Output** | Results read aloud via gTTS in Hindi, Marathi, Tamil, English |
| 🌐 **4 Languages** | Full UI + disease guidance + scheme questions in EN / HI / MR / TA |
| 💰 **Scheme Finder** | 25+ Central + state schemes matched to farmer's location and situation |
| 🗺️ **All 28 States** | State → District dropdown — no typing errors, covers all of India |
| 📱 **WhatsApp Ready** | Backend architecture supports WhatsApp Cloud API (Phase 4 stub) |
| 🔒 **No Data Stored** | Zero farmer data retained — privacy by design |

---

## 🏗️ Project Structure

farmer-ai/
├── backend/
│ ├── main.py # FastAPI app entry point
│ ├── requirements.txt # Python dependencies
│ ├── routes/
│ │ ├── diagnosis.py # POST /diagnose
│ │ ├── schemes.py # POST /schemes/session/start & /answer
│ │ └── voice.py # POST /voice/transcribe & /voice/speak
│ ├── services/
│ │ ├── disease_model.py # MobileNetV3 inference
│ │ ├── treatment.py # Disease guidance lookup (EN + i18n)
│ │ ├── scheme_engine.py # Deterministic scheme matcher
│ │ ├── scheme_conversation.py # Multi-turn Q&A session manager
│ │ ├── speech.py # Whisper STT + gTTS TTS
│ │ └── i18n.py # String lookup helper
│ ├── data/
│ │ ├── diseases.json # Verified disease guidance (ICAR sources)
│ │ ├── diseases_i18n.json # Translated disease content (HI/MR/TA)
│ │ ├── schemes.json # Maharashtra + Central schemes
│ │ └── i18n.json # All UI strings in 4 languages
│ ├── model/
│ │ └── model.pt # Trained MobileNetV3 checkpoint (~6 MB)
│ └── static/
│ └── index.html # Full frontend (zero dependencies)
└── model/
└── train.py # Training script


---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- ffmpeg installed on system PATH

**Install ffmpeg:**
```bash
# Windows — download from https://ffmpeg.org/download.html and add bin/ to PATH
# Mac
brew install ffmpeg
# Linux
sudo apt install ffmpeg
```

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourname/kisango.git](https://github.com/AshwathGreat/HACKATHON-PROJECT
cd kisango/farmer-ai/backend

# 2. Create virtual environment
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Place your trained model
# Copy model.pt to farmer-ai/model/model.pt

# 5. Start the server
uvicorn main:app --reload
```

### Open in browser

http://localhost:8000


---

## 🧠 Model Training

The disease detection model is trained on the **PlantVillage dataset** (7 tomato disease classes).

```bash
# Download dataset from Kaggle
kaggle datasets download -d emmarex/plantdisease

# Filter to tomato classes and split 80/20
python model/train.py --epochs 10 --batch-size 32
```

**Training details:**
- Architecture: MobileNetV3-Small (transfer learning)
- Strategy: Freeze backbone → train head → unfreeze → fine-tune
- Dataset: PlantVillage (tomato subset, ~18,000 images)
- Train/Val split: 80/20
- Best accuracy: ~94% on validation set

**Classes detected:**
1. Tomato — Healthy
2. Tomato — Early Blight *(Alternaria solani)*
3. Tomato — Late Blight *(Phytophthora infestans)*
4. Tomato — Leaf Mold
5. Tomato — Septoria Leaf Spot
6. Tomato — Spider Mites
7. Tomato — Yellow Leaf Curl Virus

---

## 🌐 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/diagnose` | Upload leaf image → disease + treatment in chosen language |
| `POST` | `/schemes/session/start` | Begin scheme eligibility conversation |
| `POST` | `/schemes/session/answer` | Submit answer → next question or final results |
| `POST` | `/voice/transcribe` | Audio file → transcribed text (Whisper) |
| `POST` | `/voice/speak` | Text → MP3 audio (gTTS) |
| `GET` | `/i18n` | All UI strings in all 4 languages |
| `GET` | `/health` | Health check |

**Example — Diagnose:**
```bash
curl -X POST http://localhost:8000/diagnose \
  -F "file=@leaf.jpg" \
  -F "language=mr"
```

**Response:**
```json
{
  "crop": "Tomato",
  "disease": "Early Blight (Alternaria solani)",
  "confidence": 0.945,
  "symptoms": "पूर्वीच्या/खालच्या पानांवर गडद वलय डाग...",
  "immediate_actions": ["...", "..."],
  "prevention": ["...", "..."],
  "source": "ICAR-IARI, UC-IPM"
}
```

---

## 🗣️ Languages

| Language | Code | Voice Input | Voice Output | UI | Disease Content |
|----------|------|------------|-------------|-----|----------------|
| English | `en` | ✅ | ✅ | ✅ | ✅ |
| Hindi | `hi` | ✅ | ✅ | ✅ | ✅ |
| Marathi | `mr` | ✅ | ✅ | ✅ | ✅ |
| Tamil | `ta` | ✅ | ✅ | ✅ | ✅ |

> **Note:** Disease names remain in English (scientific/citation terms). All other content is fully translated.

---

## 💰 Government Schemes Covered

### Central Government (All States)
| Scheme | Benefit |
|--------|---------|
| PM-KISAN | ₹6,000/year direct income support |
| PMFBY | Crop insurance at 2% premium |
| KCC | Crop loans at 4% effective interest |
| PMKSY | Up to 55% subsidy on drip/sprinkler irrigation |
| e-NAM | Online market access across India |
| PKVY | ₹50,000/hectare for organic farming |
| SMAM | Up to 50% subsidy on farm equipment |
| RKVY-RAFTAAR | Agriculture infrastructure funding |

### State-Specific
Maharashtra · Punjab · Haryana · Uttar Pradesh · Gujarat · Rajasthan · Tamil Nadu · Karnataka · Andhra Pradesh · Telangana · West Bengal · Madhya Pradesh · Odisha · Bihar

---

## 🛠️ Tech Stack

### Backend
- **FastAPI** — REST API framework
- **Uvicorn** — ASGI server
- **PyTorch + torchvision** — ML inference
- **Pillow** — Image preprocessing
- **OpenAI Whisper** — Local speech-to-text (no API key needed)
- **gTTS** — Google Text-to-Speech
- **ffmpeg** — Audio format conversion

### Frontend
- **Vanilla HTML + CSS + JavaScript** — Zero dependencies, fast on 2G
- **Web MediaRecorder API** — Browser-based voice recording
- **HTML5 Audio** — Voice output playback
- **localStorage** — Language preference persistence

### ML / Data
- **MobileNetV3-Small** — Lightweight CNN for edge deployment
- **PlantVillage Dataset** — 50,000+ plant disease images
- **ICAR + UC-IPM** — Verified disease knowledge base

---

## 🗺️ Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ Done | Dataset prep + MobileNetV3 training |
| Phase 2 | ✅ Done | FastAPI `/diagnose` endpoint |
| Phase 3 | ✅ Done | Web frontend with full UI |
| Phase 4 | 🔧 Stub | WhatsApp Cloud API webhook |
| Phase 5 | 🔧 Stub | WhatsApp voice message handling |
| Phase 6 | ✅ Done | Voice input (Whisper) + output (gTTS) |
| Phase 7 | ✅ Done | Scheme eligibility engine + conversation |

---

## ⚠️ Important Disclaimers

- Disease guidance is sourced from **ICAR-IARI** and **UC-IPM** resources. Always confirm diagnosis with a local agricultural officer before spending on treatment.
- Scheme information is from official **.gov.in** sources. Eligibility results are **potentially relevant** — not a guarantee. Confirm with your local Krishi Vibhag / bank / CSC.
- Whisper accuracy for Marathi and Tamil is good but not perfect — test before demo.

---



## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <strong>🌾 KisanGo — Empowering farmers with AI, in their language.</strong><br/>
  Smart India Hackathon 2026
</div>
