"""
PHASE 4/5 STUB - not yet implemented, and NOT included in main.py yet.

Will hold:
  - GET /webhook  -> Meta's verification handshake (hub.challenge)
  - POST /webhook -> receives incoming WhatsApp messages (text/image/audio),
                     routes them to /diagnose, schemes engine, or speech
                     services, and sends a reply back via the
                     WhatsApp Cloud API.

We're building this in Phase 4 of the README, once /diagnose (Phase 2) and
the test web page (Phase 3) are confirmed working. Building WhatsApp first
makes debugging much harder, since you can't easily see what the model is
doing - so we deliberately save it for later.
"""

from fastapi import APIRouter

router = APIRouter()

# Implementation added in Phase 4 - see README.md
