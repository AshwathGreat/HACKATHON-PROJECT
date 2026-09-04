import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Allow `from services...` / `from routes...` imports regardless of cwd
sys.path.insert(0, str(Path(__file__).resolve().parent))

load_dotenv()

from routes import diagnosis, schemes  # noqa: E402
# from routes import whatsapp, voice   # <- uncomment in Phase 4 / Phase 6

app = FastAPI(
    title="Farmer AI Assistant - Backend",
    description="Voice-first, multilingual agricultural assistant API "
                 "(SIH 2026 - Government of Maharashtra problem statement).",
    version="0.1.0",
)

# Permissive CORS for the local test page (Phase 3). Tighten before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(diagnosis.router, tags=["diagnosis"])
app.include_router(schemes.router, tags=["schemes"])
# app.include_router(whatsapp.router, tags=["whatsapp"])  # Phase 4
# app.include_router(voice.router, tags=["voice"])        # Phase 6

@app.get("/health")
async def health():
    return {"status": "ok"}


# Serve the simple test web page (Phase 3) at /
# IMPORTANT: this StaticFiles mount must be added LAST. Starlette matches
# routes in registration order, and a mount at "/" acts as a catch-all -
# if it were added before /health, /diagnose etc., it would shadow them.
static_dir = Path(__file__).resolve().parent / "static"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=True,
    )
