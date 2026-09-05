import os
import sys
import json
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).resolve().parent))
load_dotenv()

from routes import diagnosis, schemes, voice  # noqa: E402
# from routes import whatsapp   # Phase 4

app = FastAPI(title="Farmer AI Assistant", version="0.3.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(diagnosis.router, tags=["diagnosis"])
app.include_router(schemes.router,   tags=["schemes"])
app.include_router(voice.router,     tags=["voice"])

@app.get("/health")
async def health():
    return {"status": "ok"}

# Serve i18n strings to the frontend
_I18N_PATH = Path(__file__).resolve().parent / "data" / "i18n.json"

@app.get("/i18n")
async def i18n():
    with open(_I18N_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Remove internal _readme key before sending to frontend
    data.pop("_readme", None)
    return JSONResponse(content=data)

# Static files LAST (catch-all)
static_dir = Path(__file__).resolve().parent / "static"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=os.getenv("HOST","0.0.0.0"),
                port=int(os.getenv("PORT",8000)), reload=True)
