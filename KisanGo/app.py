import os
import logging
from typing import Optional, List
from pathlib import Path
import json
from fastapi import FastAPI, Form, File, UploadFile, Request, Response, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv
from PIL import Image
import io

from models import CropDiagnosis, TextQueryRequest
from detector import diagnose_crop_image, answer_follow_up
from session_store import session_manager
from services.scheme_engine import find_potentially_relevant_schemes, normalize_state
from services.scheme_conversation import (
    start_session as start_scheme_session_svc,
    answer_session as answer_scheme_session_svc,
    format_scheme_question_whatsapp,
    format_scheme_results_whatsapp,
    build_whatsapp_interactive_payload
)
from services.i18n import get_all_strings, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app_debug.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("agridoc.app")

app = FastAPI(
    title="KisanGo WhatsApp Bot - Crop Disease Diagnosis & Farmer Schemes",
    description="Multimodal WhatsApp assistant for farmers powered by PyTorch MobileNetV3 and verified agricultural databases.",
    version="2.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static and sample folders
os.makedirs("static", exist_ok=True)
os.makedirs("sample_images", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/sample_images", StaticFiles(directory="sample_images"), name="sample_images")


@app.get("/health")
async def health_check():
    """Health check showing status of the bot, CV model, and deterministic knowledge bases."""
    model_path = os.path.join("model", "model.pt")
    diseases_path = os.path.join("data", "diseases.json")
    schemes_path = os.path.join("data", "schemes.json")
    states_path = os.path.join("data", "states.json")
    return {
        "status": "online",
        "service": "KisanGo WhatsApp Bot (Zero-LLM Architecture)",
        "model_loaded": os.path.exists(model_path),
        "model_file": model_path,
        "database_diseases": os.path.exists(diseases_path),
        "database_schemes": os.path.exists(schemes_path),
        "database_states": os.path.exists(states_path),
        "confidence_threshold": float(os.getenv("MODEL_CONFIDENCE_THRESHOLD", "0.55")),
        "supported_webhooks": ["Twilio (/webhook/whatsapp)", "Meta Cloud API (/webhook)"]
    }


def process_farmer_text(from_id: str, text_body: str) -> tuple[str, Optional[dict]]:
    """
    Unified text processing logic for both Meta WhatsApp Cloud API and Twilio Webhooks.
    Returns:
      (reply_text, interactive_payload)
      interactive_payload is a WhatsApp Cloud API Interactive Message (Dropdown List / Buttons)
      when asking a scheme questionnaire question.
    """
    session = session_manager.get_or_create(from_id)
    lower_text = text_body.lower().strip()
    session.add_message("user", text_body)

    # 1. Explicit Language Switch
    if lower_text in ["hindi", "हिन्दी", "हिंदी"]:
        session_manager.set_language(from_id, "hi")
        reply = "🌾 *नमस्ते!* अब *KisanGo* (किसानगो) आपसे हिंदी में संवाद करेगा। अपनी बीमार फसल या पत्ती की फोटो भेजें! 📸🌱\n\n_(भाषा बदलने के लिए किसी भी समय 'main menu' दबाएं)_"
        session.add_message("assistant", reply)
        return reply, None
    elif lower_text in ["marathi", "मराठी"]:
        session_manager.set_language(from_id, "mr")
        reply = "🌾 *नमस्कार!* आता *KisanGo* (किसानगो) आपल्याशी मराठीत संवाद साधेल. आपल्या पिकाचा फोटो पाठवा! 📸🌱\n\n_(भाषा बदलण्यासाठी कधीही 'main menu' दाबा)_"
        session.add_message("assistant", reply)
        return reply, None
    elif lower_text in ["english", "en"]:
        session_manager.set_language(from_id, "en")
        reply = "🌾 *Language set to English!* I am *KisanGo*. Please send a photo of your affected crop or leaf, or type *schemes*! 📸🌱\n\n_(Type 'main menu' at any time to change language)_"
        session.add_message("assistant", reply)
        return reply, None
    elif lower_text in ["tamil", "தமிழ்"]:
        session_manager.set_language(from_id, "ta")
        reply = "🌾 *வணக்கம்!* இப்போது *KisanGo* (கிசான்கோ) உங்களுடன் தமிழில் உரையாடும். உங்கள் பயிர் அல்லது இலையின் புகைப்படத்தை அனுப்பவும்! 📸🌱\n\n_(மொழியை மாற்ற எந்த நேரத்திலும் 'main menu' ஐ அழுத்தவும்)_"
        session.add_message("assistant", reply)
        return reply, None

    # 2. Cancel active scheme questionnaire or end conversation
    if lower_text in ["cancel", "exit", "stop", "abort", "रद्द", "थांबा", "end_chat"]:
        if session.has_active_scheme_flow():
            session.clear_scheme_flow()
        reply = "🛑 *Conversation Ended.*\n\nThank you for using KisanGo! You can send a new crop photo or type *hi* anytime to start again. 🌱"
        if session.language == "hi":
            reply = "🛑 *चैट समाप्त।*\n\nKisanGo का उपयोग करने के लिए धन्यवाद! आप फिर से शुरू करने के लिए कभी भी नई फसल की फोटो भेज सकते हैं। 🌱"
        elif session.language == "mr":
            reply = "🛑 *चॅट संपले।*\n\nKisanGo वापरल्याबद्दल धन्यवाद! पुन्हा सुरू करण्यासाठी तुम्ही कधीही पिकाचा नवीन फोटो पाठवू शकता. 🌱"
        elif session.language == "ta":
            reply = "🛑 *அரட்டை முடிந்தது.*\n\nKisanGo ஐப் பயன்படுத்தியதற்கு நன்றி! நீங்கள் மீண்டும் தொடங்க எந்த நேரத்திலும் பயிர் புகைப்படத்தை அனுப்பலாம். 🌱"
        
        session.add_message("assistant", reply)
        return reply, None

    # 2.2 Main Menu intercept
    if lower_text == "main_menu":
        if session.has_active_scheme_flow():
            session.clear_scheme_flow()
        # Let it fall through to Block 5
        
    def _get_post_schemes_interactive_payload(language: str, to_number: str) -> dict:
        main_menu_title = "🔙 Main Menu"
        end_chat_title = "🛑 End Chat"
        if language == "hi":
            main_menu_title = "🔙 मुख्य मेनू"
            end_chat_title = "🛑 चैट समाप्त करें"
        elif language == "mr":
            main_menu_title = "🔙 मुख्य मेनू"
            end_chat_title = "🛑 चॅट संपवा"
        elif language == "ta":
            main_menu_title = "🔙 முதன்மை மெனு"
            end_chat_title = "🛑 அரட்டையை முடி"
            
        return {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": "What would you like to do next?" if language == "en" else ("आगे क्या करना चाहेंगे?" if language == "hi" else ("पुढे काय करायचे?" if language == "mr" else "அடுத்து என்ன செய்ய வேண்டும்?"))},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": "main_menu", "title": main_menu_title}},
                        {"type": "reply", "reply": {"id": "end_chat", "title": end_chat_title}}
                    ]
                }
            }
        }

    # 2.5 Quick scheme views
    if lower_text == "view_state_schemes":
        state_val = session.last_known_state
        if session.has_active_scheme_flow() and session.last_scheme_step:
            ans = session.last_scheme_step.get("answers", {})
            if ans.get("state"):
                state_val = ans["state"]
        session.clear_scheme_flow()
        st = state_val or "All India"
        reply = answer_follow_up(session.last_diagnosis, "schemes", language=session.language, state=st)
        session.add_message("assistant", reply)
        return reply, _get_post_schemes_interactive_payload(session.language, from_id)
        
    if lower_text == "view_all_schemes":
        session.clear_scheme_flow()
        reply = answer_follow_up(session.last_diagnosis, "schemes", language=session.language, state="All India")
        session.add_message("assistant", reply)
        return reply, _get_post_schemes_interactive_payload(session.language, from_id)

    # 3. Active scheme questionnaire ongoing (User answering questions)
    if session.has_active_scheme_flow():
        res = session.answer_scheme_flow(text_body)
        if res.get("done"):
            if res.get("error"):
                reply = f"⚠️ {res['error']}\n\nType *schemes* to check government schemes again."
            else:
                reply = format_scheme_results_whatsapp(res, language=session.language)
                
                # Use translated buttons
                main_menu_title = "🔙 Main Menu"
                end_chat_title = "🛑 End Chat"
                if session.language == "hi":
                    main_menu_title = "🔙 मुख्य मेनू"
                    end_chat_title = "🛑 चैट समाप्त करें"
                elif session.language == "mr":
                    main_menu_title = "🔙 मुख्य मेनू"
                    end_chat_title = "🛑 चॅट संपवा"
                elif session.language == "ta":
                    main_menu_title = "🔙 முதன்மை மெனு"
                    end_chat_title = "🛑 அரட்டையை முடி"
                    
                interactive_payload = {
                    "messaging_product": "whatsapp",
                    "to": from_id,
                    "type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {"text": "What would you like to do next?"},
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "main_menu", "title": main_menu_title}},
                                {"type": "reply", "reply": {"id": "end_chat", "title": end_chat_title}}
                            ]
                        }
                    }
                }
            session.add_message("assistant", reply)
            return reply, interactive_payload if 'interactive_payload' in locals() else None
        else:
            reply = format_scheme_question_whatsapp(res, language=session.language)
            interactive_payload = build_whatsapp_interactive_payload(from_id, res, language=session.language)
            if interactive_payload:
                interactive_payload["interactive"]["body"]["text"] = reply
            session.add_message("assistant", reply)
            return reply, interactive_payload

    # 4. Initiate scheme eligibility flow
    scheme_triggers = [
        "scheme", "schemes", "yojana", "subsidy", "bima", "pmfby", "pmkisan",
        "pm-kisan", "kisan card", "kcc", "insurance", "compensation", "grant", "2"
    ]
    if lower_text in scheme_triggers or any(t in lower_text for t in ["scheme", "yojana", "subsidy", "bima", "fasal bima", "anudan"]):
        prefill = {}
        if session.last_diagnosis and session.last_diagnosis.crop_name:
            prefill["crop"] = session.last_diagnosis.crop_name

        res = session.start_scheme_flow(language=session.language, prefill=prefill)
        reply = format_scheme_question_whatsapp(res, language=session.language)
        if prefill.get("crop"):
            if session.language == "hi":
                crop_note = f"🌾 _नोट: पाई गई फसल *{prefill['crop']}* का उपयोग किया जाएगा।_\n\n"
            elif session.language == "mr":
                crop_note = f"🌾 _टीप: आढळलेले पीक *{prefill['crop']}* वापरले जाईल._\n\n"
            elif session.language == "ta":
                crop_note = f"🌾 _குறிப்பு: கண்டறியப்பட்ட பயிர் *{prefill['crop']}* பயன்படுத்தப்படும்._\n\n"
            else:
                crop_note = f"🌾 _Note: Detected crop *{prefill['crop']}* will be used automatically._\n\n"
            reply = crop_note + reply
            
        interactive_payload = build_whatsapp_interactive_payload(from_id, res, language=session.language)
        if interactive_payload:
            interactive_payload["interactive"]["body"]["text"] = reply
        session.add_message("assistant", reply)
        return reply, interactive_payload

    # 5. Greeting / Menu
    if not lower_text or lower_text in ["hi", "hello", "hey", "start", "menu", "main_menu", "help", "info", "namaste"]:
        lang = session.language
        if not lang:
            lang = "en"
            session.language = "en"
        
        if lang == "hi":
            reply = "📸 *बीमारी की जांच:* बस फसल की एक फोटो भेजें!\n\nया नीचे दिए गए विकल्पों में से चुनें:"
            header_text = "🌾 KisanGo में आपका स्वागत है!"
            footer_text = "मुख्य मेनू"
            button_text = "मुख्य मेनू ▾"
            schemes_title = "🏛️ सरकारी योजनाएं"
            schemes_desc = "28 राज्यों के लिए पात्रता जांचें"
        elif lang == "mr":
            reply = "📸 *रोगाचे निदान:* फक्त पिकाचा फोटो पाठवा!\n\nकिंवा खालील पर्यायांमधून निवडा:"
            header_text = "🌾 KisanGo मध्ये आपले स्वागत आहे!"
            footer_text = "मुख्य मेनू"
            button_text = "मुख्य मेनू ▾"
            schemes_title = "🏛️ सरकारी योजना"
            schemes_desc = "२८ राज्यांसाठी पात्रता तपासा"
        elif lang == "ta":
            reply = "📸 *நோய் கண்டறிதல்:* பயிர் புகைப்படத்தை அனுப்பவும்!\n\nஅல்லது கீழே உள்ள விருப்பங்களில் ஒன்றைத் தேர்ந்தெடுக்கவும்:"
            header_text = "🌾 KisanGo விற்கு வரவேற்கிறோம்!"
            footer_text = "முதன்மை மெனு"
            button_text = "முதன்மை மெனு ▾"
            schemes_title = "🏛️ அரசு திட்டங்கள்"
            schemes_desc = "28 மாநிலங்களுக்கான தகுதியைச் சரிபார்க்கவும்"
        else:
            reply = (
                "📸 *Diagnose Disease:* Just send a crop photo!\n\n"
                "Or select an option below:"
            )
            header_text = "🌾 Welcome to KisanGo!"
            footer_text = "Main Menu"
            button_text = "Main Menu ▾"
            schemes_title = "🏛️ Govt Schemes"
            schemes_desc = "Check eligibility for 28 states"

        interactive_payload = {
            "messaging_product": "whatsapp",
            "to": from_id,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {"type": "text", "text": header_text},
                "body": {"text": reply},
                "footer": {"text": footer_text},
                "action": {
                    "button": button_text,
                    "sections": [
                        {
                            "title": "Options" if lang == "en" else ("विकल्प" if lang == "hi" else ("पर्याय" if lang == "mr" else "விருப்பங்கள்")),
                            "rows": [
                                {"id": "schemes", "title": schemes_title, "description": schemes_desc}
                            ]
                        },
                        {
                            "title": "Change Language" if lang == "en" else ("भाषा बदलें" if lang == "hi" else ("भाषा बदला" if lang == "mr" else "மொழியை மாற்று")),
                            "rows": [
                                {"id": "hindi", "title": "🗣️ हिंदी (Hindi)", "description": "हिंदी में बदलें"},
                                {"id": "marathi", "title": "🗣️ मराठी (Marathi)", "description": "मराठीत बदला"},
                                {"id": "tamil", "title": "🗣️ தமிழ் (Tamil)", "description": "தமிழுக்கு மாற்றவும்"},
                                {"id": "english", "title": "🗣️ English", "description": "Change to English"}
                            ]
                        }
                    ]
                }
            }
        }
        session.add_message("assistant", reply)
        return reply, interactive_payload

    # 6. General follow-up query
    reply = answer_follow_up(session.last_diagnosis, text_body, language=session.language, state=session.last_known_state or "All India")
    
    lang = session.language
    if not lang:
        lang = "en"
        
    interactive_payload = {
        "messaging_product": "whatsapp",
        "to": from_id,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "🌾 KisanGo"},
            "body": {"text": "Select an option to continue:" if lang == "en" else ("आगे बढ़ने के लिए चुनें:" if lang == "hi" else ("पुढे जाण्यासाठी निवडा:" if lang == "mr" else "தொடர ஒரு விருப்பத்தைத் தேர்ந்தெடுக்கவும்:"))},
            "footer": {"text": "Main Menu" if lang == "en" else ("मुख्य मेनू" if lang == "hi" else ("मुख्य मेनू" if lang == "mr" else "முதன்மை மெனு"))},
            "action": {
                "button": "Main Menu ▾" if lang == "en" else ("मुख्य मेनू ▾" if lang == "hi" else ("मुख्य मेनू ▾" if lang == "mr" else "முதன்மை மெனு ▾")),
                "sections": [
                    {
                        "title": "Options" if lang == "en" else ("विकल्प" if lang == "hi" else ("पर्याय" if lang == "mr" else "விருப்பங்கள்")),
                        "rows": [
                            {"id": "schemes", "title": "🏛️ Govt Schemes" if lang == "en" else ("🏛️ सरकारी योजनाएं" if lang == "hi" else ("🏛️ सरकारी योजना" if lang == "mr" else "🏛️ அரசு திட்டங்கள்")), "description": "Check eligibility" if lang == "en" else ("पात्रता जांचें" if lang == "hi" else ("पात्रता तपासा" if lang == "mr" else "தகுதியை சரிபார்க்கவும்"))}
                        ]
                    },
                    {
                        "title": "Change Language" if lang == "en" else ("भाषा बदलें" if lang == "hi" else ("भाषा बदला" if lang == "mr" else "மொழியை மாற்று")),
                        "rows": [
                            {"id": "hindi", "title": "🗣️ हिंदी (Hindi)", "description": "हिंदी में बदलें"},
                            {"id": "marathi", "title": "🗣️ मराठी (Marathi)", "description": "मराठीत बदला"},
                            {"id": "tamil", "title": "🗣️ தமிழ் (Tamil)", "description": "தமிழுக்கு மாற்றவும்"},
                            {"id": "english", "title": "🗣️ English", "description": "Change to English"}
                        ]
                    }
                ]
            }
        }
    }

    session.add_message("assistant", reply)
    return reply, interactive_payload





# ==========================================
# 2. META WHATSAPP CLOUD API WEBHOOK
# ==========================================
@app.get("/webhook")
async def meta_webhook_verification(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    """Meta verification handshake (hub.challenge) for WhatsApp Cloud API."""
    expected_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "agridoc_verify_token")
    valid_tokens = {expected_token, "kisango_verify_token", "agridoc_verify_token"}
    if hub_mode == "subscribe" and hub_verify_token in valid_tokens:
        logger.info(f"Meta WhatsApp Cloud API webhook verified successfully with token: {hub_verify_token}")
        return PlainTextResponse(content=hub_challenge or "")
    logger.warning(f"Verification mismatch: received '{hub_verify_token}', expected '{expected_token}'")
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@app.post("/webhook")
async def meta_whatsapp_webhook(request: Request):
    """
    Receives incoming WhatsApp messages from Meta WhatsApp Cloud API.
    Handles text, images, and interactive dropdown/button clicks.
    """
    load_dotenv(override=True)
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip()
    configured_phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip()

    try:
        body = await request.json()
        logger.info(f"Incoming Meta Webhook payload: {body}")
    except Exception as e:
        logger.error(f"[ERROR] Error parsing Meta webhook JSON: {e}")
        return JSONResponse({"status": "ignored"})

    entry_list = body.get("entry", [])
    if not entry_list:
        return JSONResponse({"status": "ok"})

    for entry in entry_list:
        for change in entry.get("changes", []):
            val = change.get("value", {})
            messages = val.get("messages", [])
            metadata = val.get("metadata", {})
            phone_number_id = metadata.get("phone_number_id") or configured_phone_id

            for msg in messages:
                from_number = msg.get("from")
                msg_type = msg.get("type")
                print(f"[MSG] Message from {from_number} | Type: {msg_type}", flush=True)
                session = session_manager.get_or_create(from_number)

                reply_text = ""
                interactive_payload = None

                # Handle interactive selection (list dropdown reply or button reply)
                if msg_type == "interactive":
                    interactive = msg.get("interactive", {})
                    itype = interactive.get("type")
                    if itype == "list_reply":
                        text_body = interactive.get("list_reply", {}).get("id") or interactive.get("list_reply", {}).get("title", "")
                    elif itype == "button_reply":
                        text_body = interactive.get("button_reply", {}).get("id") or interactive.get("button_reply", {}).get("title", "")
                    else:
                        text_body = ""
                    logger.info(f"[INTERACTIVE] Selection Received: '{text_body}'")
                    reply_text, interactive_payload = process_farmer_text(from_number, text_body)

                # Handle text
                elif msg_type == "text":
                    text_body = msg.get("text", {}).get("body", "")
                    logger.info(f"[TEXT] Text received: '{text_body}'")
                    reply_text, interactive_payload = process_farmer_text(from_number, text_body)

                # Handle image
                elif msg_type == "image":
                    is_answering_crop = False
                    if session.has_active_scheme_flow():
                        if session.last_scheme_step and session.last_scheme_step.get("field") == "crop":
                            is_answering_crop = True
                        else:
                            session.clear_scheme_flow()
                    else:
                        session.clear_scheme_flow()

                    image_id = msg.get("image", {}).get("id")
                    caption = msg.get("image", {}).get("caption", "")
                    print(f"[IMAGE] Image received (ID: {image_id})", flush=True)

                    if image_id and access_token:
                        # Download media URL from Meta Graph API
                        async with httpx.AsyncClient() as client:
                            media_resp = await client.get(
                                f"https://graph.facebook.com/v18.0/{image_id}",
                                headers={"Authorization": f"Bearer {access_token}"}
                            )
                            if media_resp.status_code == 200:
                                download_url = media_resp.json().get("url")
                                dl_resp = await client.get(
                                    download_url,
                                    headers={"Authorization": f"Bearer {access_token}"}
                                )
                                if dl_resp.status_code == 200:
                                    # Use previously known state from session if available
                                    known_state = "All India"
                                    if session.last_diagnosis and hasattr(session, "last_known_state"):
                                        known_state = session.last_known_state or "All India"
                                    diag = diagnose_crop_image(dl_resp.content, user_caption=caption, language=session.language, state=known_state)
                                    session_manager.update_diagnosis(from_number, diag)
                                    
                                    if is_answering_crop:
                                        # Use the detected crop to answer the flow
                                        res = session.answer_scheme_flow(diag.crop_name)
                                        reply_text = diag.farmer_friendly_summary + "\n\n" + format_scheme_question_whatsapp(res, language=session.language)
                                        interactive_payload = build_whatsapp_interactive_payload(from_number, res, language=session.language)
                                        if interactive_payload:
                                            interactive_payload["interactive"]["body"]["text"] = format_scheme_question_whatsapp(res, language=session.language)
                                    else:
                                        reply_text = diag.farmer_friendly_summary
                                        
                                        main_menu_title = "🔙 Main Menu"
                                        schemes_title = "🏛️ Govt Schemes"
                                        end_chat_title = "🛑 End Chat"
                                        
                                        if session.language == "hi":
                                            main_menu_title = "🔙 मुख्य मेनू"
                                            schemes_title = "🏛️ सरकारी योजनाएं"
                                            end_chat_title = "🛑 चैट समाप्त करें"
                                        elif session.language == "mr":
                                            main_menu_title = "🔙 मुख्य मेनू"
                                            schemes_title = "🏛️ सरकारी योजना"
                                            end_chat_title = "🛑 चॅट संपवा"
                                        elif session.language == "ta":
                                            main_menu_title = "🔙 முதன்மை மெனு"
                                            schemes_title = "🏛️ அரசு திட்டங்கள்"
                                            end_chat_title = "🛑 அரட்டையை முடி"
                                            
                                        interactive_payload = {
                                            "messaging_product": "whatsapp",
                                            "to": from_number,
                                            "type": "interactive",
                                            "interactive": {
                                                "type": "button",
                                                "body": {"text": "Select an option to continue:" if session.language == "en" else ("आगे बढ़ने के लिए चुनें:" if session.language == "hi" else ("पुढे जाण्यासाठी निवडा:" if session.language == "mr" else "தொடர ஒரு விருப்பத்தைத் தேர்ந்தெடுக்கவும்:"))},
                                                "action": {
                                                    "buttons": [
                                                        {"type": "reply", "reply": {"id": "main_menu", "title": main_menu_title}},
                                                        {"type": "reply", "reply": {"id": "schemes", "title": schemes_title}},
                                                        {"type": "reply", "reply": {"id": "end_chat", "title": end_chat_title}}
                                                    ]
                                                }
                                            }
                                        }
                    if not reply_text:
                        reply_text = "⚠️ Could not download the image from WhatsApp. Please check Meta access token or try again."

                # Send reply back via Meta Cloud API if configured
                if (reply_text or interactive_payload) and phone_number_id and access_token:
                    print(f"[SEND] Sending reply to {from_number} via Meta Cloud API...", flush=True)
                    try:
                        async with httpx.AsyncClient(timeout=10.0) as client:
                            # 1. If both are present, send text first
                            interactive_body = interactive_payload.get("interactive", {}).get("body", {}).get("text", "") if interactive_payload else ""
                            should_send_text_separately = reply_text and (reply_text != interactive_body)

                            if should_send_text_separately and interactive_payload:
                                await client.post(
                                    f"https://graph.facebook.com/v18.0/{phone_number_id}/messages",
                                    headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                                    json={
                                        "messaging_product": "whatsapp",
                                        "to": from_number,
                                        "type": "text",
                                        "text": {"body": reply_text}
                                    }
                                )
                                # Then send interactive payload
                                send_resp = await client.post(
                                    f"https://graph.facebook.com/v18.0/{phone_number_id}/messages",
                                    headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                                    json=interactive_payload
                                )
                            # 2. If only interactive payload
                            elif interactive_payload:
                                send_resp = await client.post(
                                    f"https://graph.facebook.com/v18.0/{phone_number_id}/messages",
                                    headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                                    json=interactive_payload
                                )
                            # 3. If only text
                            else:
                                send_resp = await client.post(
                                    f"https://graph.facebook.com/v18.0/{phone_number_id}/messages",
                                    headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                                    json={
                                        "messaging_product": "whatsapp",
                                        "to": from_number,
                                        "type": "text",
                                        "text": {"body": reply_text}
                                    }
                                )
                                
                            print(f"[SEND STATUS] Meta API Send Status: {send_resp.status_code} | Body: {send_resp.text}", flush=True)
                            logger.info(f"Meta Graph API response: status={send_resp.status_code}, body={send_resp.text}")
                    except Exception as e:
                        print(f"[ERROR] Error sending Meta message: {e}", flush=True)
                        logger.error(f"Error sending Meta WhatsApp message: {e}")
                else:
                    print(f"[WARN] Cannot send reply: reply_text={bool(reply_text)}, phone_id={phone_number_id}, has_token={bool(access_token)}", flush=True)

    return JSONResponse({"status": "processed"})


# ==========================================
# 3. DIRECT REST ENDPOINTS (GITHUB REPO COMPATIBLE)
# ==========================================
class SchemeQuery(BaseModel):
    state: str = "Maharashtra"
    crop: str
    district: Optional[str] = None
    has_insurance: Optional[bool] = None
    damage_pct: Optional[float] = None
    farmer_category: Optional[str] = None


class StartSessionRequest(BaseModel):
    language: str = "en"
    crop: Optional[str] = None
    state: str = "Maharashtra"
    district: Optional[str] = None


class AnswerSessionRequest(BaseModel):
    session_id: str
    answer: str


@app.post("/diagnose")
async def diagnose_file_endpoint(
    file: UploadFile = File(...),
    language: str = Form("en")
):
    """
    Direct image diagnosis matching the GitHub repo's /diagnose contract.
    Runs PyTorch MobileNetV3 model + diseases.json lookup.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload a valid image file.")

    try:
        contents = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read the uploaded image.")

    diagnosis = diagnose_crop_image(contents, mime_type=file.content_type, language=language)

    if diagnosis.confidence_score < 0.55:
        labels = get_all_strings(language)
        return {
            "crop": diagnosis.crop_name,
            "disease": None,
            "confidence": diagnosis.confidence_score,
            "low_confidence": True,
            "message": labels.get("low_conf_msg", "I'm not confident enough about this diagnosis. Please send a clearer photo."),
            "top_k": [{"crop": diagnosis.crop_name, "disease": diagnosis.condition_name, "confidence": diagnosis.confidence_score}],
            "labels": labels
        }

    symptoms_str = diagnosis.symptoms_detected if isinstance(diagnosis.symptoms_detected, str) else "\n".join(diagnosis.symptoms_detected)
    actions = diagnosis.treatment.cultural if diagnosis.treatment else []

    return {
        "crop": diagnosis.crop_name,
        "disease": diagnosis.condition_name,
        "confidence": diagnosis.confidence_score,
        "low_confidence": False,
        "is_healthy": diagnosis.is_healthy,
        "symptoms": symptoms_str,
        "immediate_actions": actions,
        "prevention": diagnosis.preventive_measures,
        "warning": "Consult local Krishi Vibhag officer before applying chemicals in large scale." if not diagnosis.is_healthy else "",
        "source": "ICAR / PlantVillage Verified Knowledgebase",
        "farmer_friendly_summary": diagnosis.farmer_friendly_summary
    }


@app.get("/i18n")
async def i18n_endpoint():
    """Serves static i18n strings to the frontend."""
    i18n_path = Path("data") / "i18n.json"
    with open(i18n_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.pop("_readme", None)
    return JSONResponse(content=data)


@app.post("/voice/transcribe")
async def voice_transcribe_endpoint(
    file: UploadFile = File(...),
    language: str = Form("en"),
):
    """Audio to text transcription."""
    from services.speech import speech_to_text
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio received.")
    try:
        text = speech_to_text(audio_bytes, language_hint=language)
    except Exception as e:
        logger.warning(f"Voice transcription fallback: {e}")
        text = ""
    return {"text": text, "language": language}


class SpeakRequest(BaseModel):
    text: str
    language: str = "en"


@app.post("/voice/speak")
async def voice_speak_endpoint(body: SpeakRequest):
    """Text to speech synthesis."""
    from services.speech import text_to_speech
    try:
        mp3_bytes = text_to_speech(body.text, language_code=body.language)
        return Response(content=mp3_bytes, media_type="audio/mpeg")
    except Exception as e:
        logger.warning(f"Voice speak fallback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/schemes/match")
async def schemes_match_endpoint(query: SchemeQuery):
    """
    Deterministic government scheme matching from schemes.json across all 28 states.
    """
    matches = find_potentially_relevant_schemes(
        state=query.state,
        crop=query.crop,
        district=query.district,
        has_insurance=query.has_insurance,
        damage_pct=query.damage_pct,
        farmer_category=query.farmer_category
    )
    return {
        "disclaimer": (
            "These are potentially relevant schemes based on the information provided. "
            "This is not a guarantee of eligibility or approval — please confirm "
            "final eligibility and required documents with the official source or your local Krishi Vibhag / CSC."
        ),
        "count": len(matches),
        "schemes": matches
    }


@app.post("/schemes/session/start")
async def start_scheme_session_endpoint(req: StartSessionRequest):
    """Starts a multi-turn scheme questionnaire session via REST API."""
    prefill = {
        "crop": req.crop,
        "state": req.state,
        "district": req.district
    }
    return start_scheme_session_svc(language=req.language, prefill=prefill)


@app.post("/schemes/session/answer")
async def answer_scheme_session_endpoint(req: AnswerSessionRequest):
    """Submits an answer to a multi-turn scheme questionnaire session via REST API."""
    return answer_scheme_session_svc(req.session_id, req.answer)


# ==========================================
# 4. WEB SIMULATOR & TEST ENDPOINTS
# ==========================================
@app.post("/api/diagnose")
async def api_diagnose_image(
    file: UploadFile = File(...),
    session_id: str = Form("demo-farmer"),
    caption: str = Form(""),
    language: str = Form("en"),
):
    """Multipart image upload endpoint for web simulator."""
    try:
        content = await file.read()
        mime_type = file.content_type or "image/jpeg"

        session = session_manager.get_or_create(session_id)
        session.language = language
        session.clear_scheme_flow()
        session.add_message("user", caption or "Uploaded crop photo for diagnosis")

        diagnosis = diagnose_crop_image(
            image_bytes=content,
            mime_type=mime_type,
            user_caption=caption,
            language=language
        )

        session_manager.update_diagnosis(session_id, diagnosis)

        return {
            "success": True,
            "diagnosis": diagnosis.model_dump(),
            "session_id": session_id,
            "language": language
        }
    except Exception as e:
        logger.error(f"Error in /api/diagnose: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def api_chat(req: TextQueryRequest):
    """Follow-up text conversation in web simulator."""
    reply, interactive_payload = process_farmer_text(req.session_id, req.message)
    return {
        "reply": reply,
        "interactive": interactive_payload.get("interactive") if interactive_payload else None,
        "session_id": req.session_id,
        "language": req.language or "en"
    }


@app.get("/api/history/{session_id}")
async def api_get_history(session_id: str):
    """Fetches chat history for web simulator."""
    session = session_manager.get(session_id)
    if not session:
        return {"messages": []}
    return {
        "messages": [m.model_dump() for m in session.messages],
        "language": session.language,
        "has_diagnosis": session.last_diagnosis is not None,
        "has_active_scheme_flow": session.has_active_scheme_flow()
    }


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serves the KisanGo Web Application with 28 states & dropdown method."""
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>KisanGo API Online</h1><p>Visit /docs for Swagger UI</p>")
