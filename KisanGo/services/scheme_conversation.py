"""

Turns the deterministic scheme_engine.py matcher into a step-by-step

conversation: asks state -> district -> crop -> insurance -> damage ->

category, one question at a time, then returns matches.



Supports all 28 states of India + Central government schemes.

Supports PREFILLED answers (e.g. crop already known from a photo diagnosis).

Provides WhatsApp message formatters for prompt delivery.

"""



import uuid

import json
from pathlib import Path
from typing import Optional

from services.i18n import get_string
from services.scheme_engine import find_potentially_relevant_schemes, normalize_state
from services.districts import ALL_STATES_LIST, STATES_AND_DISTRICTS

# Load locales for state/district names
LOCALES_CACHE = {}
_locale_path = Path("services/locales.json")
if _locale_path.exists():
    try:
        with open(_locale_path, "r", encoding="utf-8") as _f:
            LOCALES_CACHE = json.load(_f)
    except Exception:
        pass

def _translate_location(name: str, loc_type: str, lang: str) -> str:
    lang = lang.lower()
    if "hi" in lang: target = "hi"
    elif "mr" in lang: target = "mr"
    elif "ta" in lang: target = "ta"
    else: return name
    
    return LOCALES_CACHE.get(loc_type, {}).get(name, {}).get(target, name)

# Each entry: (answer_key, i18n_question_key)
def _get_ui_strings(field: str, language: str) -> dict:
    lang = language.lower()
    
    if field == "state":
        if "hi" in lang: return {"header": "राज्य चुनें", "footer": "KisanGo • 28 राज्य", "button": "राज्य चुनें ▾", "more": "अधिक राज्य ➡️", "all_schemes": "सभी योजनाएं", "state_schemes": "राज्य की योजनाएं", "main_menu": "मुख्य मेनू 🏠", "end_chat": "चैट समाप्त करें ❌"}
        if "mr" in lang: return {"header": "राज्य निवडा", "footer": "KisanGo • 28 राज्ये", "button": "राज्य निवडा ▾", "more": "अधिक राज्ये ➡️", "all_schemes": "सर्व सरकारी योजना", "state_schemes": "राज्य योजना", "main_menu": "मुख्य मेनू 🏠", "end_chat": "चॅट संपवा ❌"}
        if "ta" in lang: return {"header": "மாநிலத்தை தேர்ந்தெடுக்கவும்", "footer": "KisanGo • 28 மாநிலங்கள்", "button": "மாநிலம் தேர்வுசெய் ▾", "more": "மேலும் மாநிலங்கள் ➡️", "all_schemes": "எல்லா திட்டங்கள்", "state_schemes": "மாநில திட்டங்கள்", "main_menu": "முதன்மை மெனு 🏠", "end_chat": "அரட்டையை முடி ❌"}
        return {"header": "🏛️ Select Your State", "footer": "KisanGo • All 28 States", "button": "Select State ▾", "more": "More States ➡️", "all_schemes": "All Govt Schemes", "state_schemes": "State Schemes", "main_menu": "Main Menu 🏠", "end_chat": "End Chat ❌"}
        
    elif field == "district":
        if "hi" in lang: return {"header": "जिला चुनें", "footer": "KisanGo - जिले", "button": "जिला चुनें", "more": "अधिक जिले ➡️", "skip": "अन्य / छोड़ें ⏭️", "state_schemes": "राज्य की योजनाएं", "all_schemes": "सभी योजनाएं", "main_menu": "मुख्य मेनू 🏠", "end_chat": "चैट समाप्त करें ❌"}
        if "mr" in lang: return {"header": "जिल्हा निवडा", "footer": "KisanGo - जिल्हे", "button": "जिल्हा निवडा", "more": "अधिक जिल्हे ➡️", "skip": "इतर / वगळा ⏭️", "state_schemes": "राज्य योजना", "all_schemes": "सर्व सरकारी योजना", "main_menu": "मुख्य मेनू 🏠", "end_chat": "चॅट संपवा ❌"}
        if "ta" in lang: return {"header": "மாவட்டத்தை தேர்ந்தெடுக்கவும்", "footer": "KisanGo - மாவட்டங்கள்", "button": "மாவட்டம் தேர்வுசெய்", "more": "மேலும் மாவட்டங்கள் ➡️", "skip": "பிற / தவிர் ⏭️", "state_schemes": "மாநில திட்டங்கள்", "all_schemes": "எல்லா திட்டங்கள்", "main_menu": "முதன்மை மெனு 🏠", "end_chat": "அரட்டையை முடி ❌"}
        return {"header": "Select District", "footer": "KisanGo - Districts", "button": "Select District", "more": "More Districts ➡️", "skip": "Other / Skip ⏭️", "state_schemes": "State Schemes", "all_schemes": "All Govt Schemes", "main_menu": "Main Menu 🏠", "end_chat": "End Chat ❌"}
        
    elif field == "has_insurance":
        if "hi" in lang: return {"header": "फसल बीमा (PMFBY)", "footer": "KisanGo - योजना की जांच", "button": "उत्तर चुनें", "yes": "हाँ - मेरे पास बीमा है", "no": "नहीं - मेरे पास नहीं है", "skip": "निश्चित नहीं / छोड़ें", "state_schemes": "राज्य की योजनाएं", "all_schemes": "सभी योजनाएं", "main_menu": "मुख्य मेनू 🏠", "end_chat": "चैट समाप्त करें ❌"}
        if "mr" in lang: return {"header": "पीक विमा (PMFBY)", "footer": "KisanGo - योजना तपासणी", "button": "उत्तर निवडा", "yes": "होय - माझ्याकडे विमा आहे", "no": "नाही - माझ्याकडे नाही", "skip": "खात्री नाही / वगळा", "state_schemes": "राज्य योजना", "all_schemes": "सर्व सरकारी योजना", "main_menu": "मुख्य मेनू 🏠", "end_chat": "चॅट संपवा ❌"}
        if "ta" in lang: return {"header": "பயிர் காப்பீடு (PMFBY)", "footer": "KisanGo - திட்ட சரிபார்ப்பு", "button": "பதில் தேர்வுசெய்", "yes": "ஆம் - காப்பீடு உள்ளது", "no": "இல்லை - என்னிடம் இல்லை", "skip": "தெரியவில்லை / தவிர்", "state_schemes": "மாநில திட்டங்கள்", "all_schemes": "எல்லா திட்டங்கள்", "main_menu": "முதன்மை மெனு 🏠", "end_chat": "அரட்டையை முடி ❌"}
        return {"header": "Crop Insurance (PMFBY)", "footer": "KisanGo - Scheme Check", "button": "Select Answer", "yes": "Yes - I have insurance", "no": "No - I don't have it", "skip": "Not Sure / Skip", "state_schemes": "State Schemes", "all_schemes": "All Govt Schemes", "main_menu": "Main Menu 🏠", "end_chat": "End Chat ❌"}
        
    elif field == "damage_pct":
        if "hi" in lang: return {"header": "फसल नुकसान का स्तर", "footer": "राहत थ्रेसहोल्ड जांच", "button": "नुकसान % चुनें", "levels": ["10% - 20%", "20% - 33%", "33% - 50%", "50% - 75%", "75% - 100%"], "desc": ["मामूली कीट/रोग नुकसान", "मध्यम फसल नुकसान", "महत्वपूर्ण आपदा नुकसान", "गंभीर फसल नुकसान", "फसल का कुल नुकसान"], "skip": "निश्चित नहीं / छोड़ें", "state_schemes": "राज्य की योजनाएं", "all_schemes": "सभी योजनाएं", "main_menu": "मुख्य मेनू 🏠", "end_chat": "चैट समाप्त करें ❌"}
        if "mr" in lang: return {"header": "पीक नुकसानीची पातळी", "footer": "मदत थ्रेशोल्ड तपासणी", "button": "नुकसान % निवडा", "levels": ["10% - 20%", "20% - 33%", "33% - 50%", "50% - 75%", "75% - 100%"], "desc": ["किरकोळ कीड/रोग नुकसान", "मध्यम पीक नुकसान", "महत्वपूर्ण आपत्ती नुकसान", "तीव्र पीक नुकसान", "पिकाचे पूर्ण नुकसान"], "skip": "खात्री नाही / वगळा", "state_schemes": "राज्य योजना", "all_schemes": "सर्व सरकारी योजना", "main_menu": "मुख्य मेनू 🏠", "end_chat": "चॅट संपवा ❌"}
        if "ta" in lang: return {"header": "பயிர் சேத நிலை", "footer": "நிவாரண வரம்பு சரிபார்ப்பு", "button": "சேத % தேர்வுசெய்", "levels": ["10% - 20%", "20% - 33%", "33% - 50%", "50% - 75%", "75% - 100%"], "desc": ["சிறிய பூச்சி/நோய் சேதம்", "மிதமான பயிர் சேதம்", "கணிசமான பேரிடர் இழப்பு", "கடுமையான பயிர் சேதம்", "மொத்த பயிர் இழப்பு"], "skip": "தெரியவில்லை / தவிர்", "state_schemes": "மாநில திட்டங்கள்", "all_schemes": "எல்லா திட்டங்கள்", "main_menu": "முதன்மை மெனு 🏠", "end_chat": "அரட்டையை முடி ❌"}
        return {"header": "Crop Damage Level", "footer": "Used to check Calamity Relief threshold", "button": "Select Damage %", "levels": ["10% - 20%", "20% - 33%", "33% - 50%", "50% - 75%", "75% - 100%"], "desc": ["Minor pest/disease damage", "Moderate crop damage", "Significant disaster loss", "Severe crop damage", "Total crop loss"], "skip": "Not Sure / Skip", "state_schemes": "State Schemes", "all_schemes": "All Govt Schemes", "main_menu": "Main Menu 🏠", "end_chat": "End Chat ❌"}
        
    elif field == "farmer_category":
        if "hi" in lang: return {"header": "किसान श्रेणी", "footer": "श्रेणी के आधार पर पात्रता", "button": "श्रेणी चुनें", "titles": ["छोटा और सीमांत", "मध्यम किसान", "बड़ा किसान", "किरायेदार किसान"], "desc": ["2 हेक्टेयर से कम", "2 से 10 हेक्टेयर", "10 हेक्टेयर से ऊपर", "बटाईदार या किरायेदार"], "skip": "छोड़ें / सामान्य", "skip_desc": "इस चरण को छोड़ें", "state_schemes": "राज्य की योजनाएं", "all_schemes": "सभी योजनाएं", "main_menu": "मुख्य मेनू 🏠", "end_chat": "चैट समाप्त करें ❌"}
        if "mr" in lang: return {"header": "शेतकरी वर्गवारी", "footer": "वर्गवारीनुसार पात्रता", "button": "वर्गवारी निवडा", "titles": ["अल्प व अत्यल्प", "मध्यम शेतकरी", "मोठा शेतकरी", "कुळ शेतकरी"], "desc": ["२ हेक्टरच्या खाली", "२ ते १० हेक्टर", "१० हेक्टरच्या वर", "बटईदार किंवा कुळ"], "skip": "वगळा / सामान्य", "skip_desc": "हा टप्पा वगळा", "state_schemes": "राज्य योजना", "all_schemes": "सर्व सरकारी योजना", "main_menu": "मुख्य मेनू 🏠", "end_chat": "चॅट संपवा ❌"}
        if "ta" in lang: return {"header": "விவசாயி வகை", "footer": "வகை சார்ந்த தகுதி", "button": "வகை தேர்வுசெய்", "titles": ["சிறு மற்றும் குறு", "நடுத்தர விவசாயி", "பெரிய விவசாயி", "குத்தகை விவசாயி"], "desc": ["2 ஹெக்டேருக்கும் கீழ்", "2 முதல் 10 ஹெக்டேர் வரை", "10 ஹெக்டேருக்கு மேல்", "குத்தகை விவசாயி"], "skip": "தவிர் / பொதுவானது", "skip_desc": "இதை தவிர்க்கவும்", "state_schemes": "மாநில திட்டங்கள்", "all_schemes": "எல்லா திட்டங்கள்", "main_menu": "முதன்மை மெனு 🏠", "end_chat": "அரட்டையை முடி ❌"}
        return {"header": "Farmer Category", "footer": "Used for category-based eligibility", "button": "Select Category", "titles": ["Small & Marginal", "Medium Farmer", "Large Farmer", "Tenant Farmer"], "desc": ["Under 2 Hectares (5 Acres)", "2 to 10 Hectares", "Above 10 Hectares", "Sharecropper or tenant"], "skip": "Skip / General", "skip_desc": "Skip this step", "state_schemes": "State Schemes", "all_schemes": "All Govt Schemes", "main_menu": "Main Menu 🏠", "end_chat": "End Chat ❌"}
    
    return {}





QUESTION_FLOW = [

    ("state", "ask_state"),

    ("district", "ask_district"),

    ("crop", "ask_crop"),

    ("has_insurance", "ask_insurance"),

    ("damage_pct", "ask_damage"),

    ("farmer_category", "ask_category"),

]



SESSIONS: dict = {}





def _parse_answer(key: str, raw_answer: str):

    """Light parsing for answers. Never raises - falls back gracefully."""

    text = raw_answer.strip()



    if key == "state":

        return normalize_state(text)



    if key == "has_insurance":

        lower = text.lower()

        if lower in ("yes", "y", "haan", "हाँ", "हो", "होय", "ஆம்"):

            return True

        if lower in ("no", "n", "nahi", "नहीं", "नाही", "இல்லை"):

            return False

        return None



    if key == "damage_pct":

        if text.lower() == "skip":

            return None

        digits = "".join(ch for ch in text if ch.isdigit())

        return float(digits) if digits else None



    if key == "farmer_category":

        if text.lower() == "skip":

            return None

        return text



    if key in ("district", "crop"):

        if text.lower() == "skip":

            return None

        return text.title()



    return text





def _finalize(session_id: str) -> dict:

    session = SESSIONS.pop(session_id, None)

    if not session:

        return {"error": "Session not found or expired."}



    language = session["language"]

    answers = session["answers"]



    state = answers.get("state") or "Maharashtra"

    crop = answers.get("crop") or ""

    district = answers.get("district")

    has_insurance = answers.get("has_insurance")

    damage_pct = answers.get("damage_pct")

    farmer_category = answers.get("farmer_category")



    matches = find_potentially_relevant_schemes(

        state=state,

        crop=crop,

        district=district,

        has_insurance=has_insurance,

        damage_pct=damage_pct,

        farmer_category=farmer_category,

    )



    return {

        "session_id": session_id,

        "done": True,

        "disclaimer": get_string("disclaimer", language),

        "no_matches_message": get_string("no_matches", language) if not matches else None,

        "count": len(matches),

        "schemes": matches,

        "answers_given": answers,

        "language": language,

    }





def start_session(language: str = "en", prefill: Optional[dict] = None) -> dict:

    """

    prefill: e.g. {"crop": "Tomato"} - these fields are stored immediately

    and skipped in the question flow.

    """

    prefill = {k: v for k, v in (prefill or {}).items() if v not in (None, "")}



    session_id = str(uuid.uuid4())

    remaining_flow = [(k, q) for k, q in QUESTION_FLOW if k not in prefill]



    SESSIONS[session_id] = {

        "language": language,

        "flow": remaining_flow,

        "step": 0,

        "answers": dict(prefill),

        "state_page": 1,

        "district_page": 1,

    }



    if not remaining_flow:

        return _finalize(session_id)



    first_key, first_q_key = remaining_flow[0]

    return {

        "session_id": session_id,

        "done": False,

        "question": get_string(first_q_key, language),

        "field": first_key,

        "step": 1,

        "total_steps": len(remaining_flow),

        "language": language,

        "answers": dict(prefill),

    }





def answer_session(session_id: str, answer: str) -> dict:

    session = SESSIONS.get(session_id)

    if session is None:

        return {"error": "Session not found or expired. Please start again.", "done": True}



    language = session["language"]

    flow = session["flow"]

    step = session["step"]

    current_key, _ = flow[step]



    # --- Intercept pagination BEFORE any parsing ---

    raw = answer.strip()

    if raw.startswith("more_states_"):

        session["state_page"] = int(raw.split("_")[-1])

        return {

            "session_id": session_id,

            "done": False,

            "question": get_string(flow[step][1], language),

            "field": current_key,

            "step": step + 1,   # display: 1-indexed

            "total_steps": len(flow),

            "language": language,

            "answers": dict(session["answers"]),

            "state_page": session["state_page"]

        }



    if raw.startswith("more_districts_"):

        session["district_page"] = int(raw.split("_")[-1])

        return {

            "session_id": session_id,

            "done": False,

            "question": get_string(flow[step][1], language),

            "field": current_key,

            "step": step + 1,   # display: 1-indexed

            "total_steps": len(flow),

            "language": language,

            "answers": dict(session["answers"]),

            "district_page": session["district_page"]

        }



    parsed_ans = _parse_answer(current_key, answer)



    session["answers"][current_key] = parsed_ans

    # Reset district page whenever a new state is selected

    if current_key == "state":

        session["district_page"] = 1

    session["step"] += 1



    if session["step"] < len(flow):

        next_key, next_q_key = flow[session["step"]]

        return {

            "session_id": session_id,

            "done": False,

            "question": get_string(next_q_key, language),

            "field": next_key,

            "step": session["step"] + 1,

            "total_steps": len(flow),

            "language": language,

            "answers": dict(session["answers"]),

            "district_page": session.get("district_page", 1),

        }



    return _finalize(session_id)





def format_scheme_question_whatsapp(data: dict, language: str = "en") -> str:

    """Formats an active questionnaire step for WhatsApp with emojis and clear instructions."""

    field = data.get("field")

    step = data.get("step", 1)

    total = data.get("total_steps", 5)



    if language == "hi":

        headers = {

            "state": (

                f"📍 *चरण {step}/{total}: राज्य चुनें*\n"

                "_(रद्द करने के लिए 'cancel' लिखें)_"

            ),

            "district": (

                f"🏙️ *चरण {step}/{total}: अपना जिला लिखें*\n"

                "_(छोड़ने के लिए 'skip' लिखें)_"

            ),

            "crop": (

                f"🌱 *चरण {step}/{total}: फसल का नाम लिखें या फसल की फोटो भेजें*"

            ),

            "has_insurance": (

                f"🛡️ *चरण {step}/{total}: क्या आपके पास फसल बीमा (PMFBY) है?*"

            ),

            "damage_pct": (

                f"📉 *चरण {step}/{total}: नुकसान का प्रतिशत चुनें*\n"

                "_(छोड़ने के लिए 'skip' लिखें)_"

            ),

            "farmer_category": (

                f"👨‍🌾 *चरण {step}/{total}: किसान श्रेणी चुनें*\n"

                "_(छोड़ने के लिए 'skip' लिखें)_"

            )

        }

    elif language == "mr":

        headers = {

            "state": (

                f"📍 *टप्पा {step}/{total}: राज्य निवडा*\n"

                "_(रद्द करण्यासाठी 'cancel' लिहा)_"

            ),

            "district": (

                f"🏙️ *टप्पा {step}/{total}: तुमचा जिल्हा लिहा*\n"

                "_(वगळण्यासाठी 'skip' लिहा)_"

            ),

            "crop": (

                f"🌱 *टप्पा {step}/{total}: पिकाचे नाव लिहा किंवा पिकाचा फोटो पाठवा*"

            ),

            "has_insurance": (

                f"🛡️ *टप्पा {step}/{total}: तुमच्याकडे पीक विमा (PMFBY) आहे का?*"

            ),

            "damage_pct": (

                f"📉 *टप्पा {step}/{total}: नुकसानीची टक्केवारी निवडा*\n"

                "_(वगळण्यासाठी 'skip' लिहा)_"

            ),

            "farmer_category": (

                f"👨‍🌾 *टप्पा {step}/{total}: शेतकरी गट निवडा*\n"

                "_(वगळण्यासाठी 'skip' टाइप करा)_"

            )

        }

    elif language == "ta":

        headers = {

            "state": (

                f"📍 *படி {step}/{total}: மாநிலத்தைத் தேர்ந்தெடுக்கவும்*\n"

                "_(வெளியேற 'cancel' எனத் தட்டச்சு செய்க)_"

            ),

            "district": (

                f"🏙️ *படி {step}/{total}: மாவட்டத்தை உள்ளிடவும்*\n"

                "_(தவிர்க்க 'skip' எனத் தட்டச்சு செய்க)_"

            ),

            "crop": (

                f"🌱 *படி {step}/{total}: பயிரின் பெயரை உள்ளிடவும் அல்லது புகைப்படத்தை அனுப்பவும்*"

            ),

            "has_insurance": (

                f"🛡️ *படி {step}/{total}: உங்களிடம் பயிர் காப்பீடு உள்ளதா?*"

            ),

            "damage_pct": (

                f"📉 *படி {step}/{total}: சேதத்தின் சதவீதத்தைத் தேர்ந்தெடுக்கவும்*\n"

                "_(தவிர்க்க 'skip' எனத் தட்டச்சு செய்க)_"

            ),

            "farmer_category": (

                f"👨‍🌾 *படி {step}/{total}: வகையைத் தேர்ந்தெடுக்கவும்*\n"

                "_(தவிர்க்க 'skip' எனத் தட்டச்சு செய்க)_"

            )

        }

    else:  # English

        headers = {

            "state": (

                f"📍 *Step {step}/{total}: Select State*\n"

                "_(Type *cancel* to exit)_"

            ),

            "district": (

                f"🏙️ *Step {step}/{total}: Enter District*\n"

                "_(Type *skip* to skip)_"

            ),

            "crop": (

                f"🌱 *Step {step}/{total}: Enter Crop Name / Send a photo of the crop*"

            ),

            "has_insurance": (

                f"🛡️ *Step {step}/{total}: Do you have crop insurance?*"

            ),

            "damage_pct": (

                f"📉 *Step {step}/{total}: Select Damage %*\n"

                "_(Type *skip* to skip)_"

            ),

            "farmer_category": (

                f"👨‍🌾 *Step {step}/{total}: Select Category*\n"

                "_(Type *skip* to skip)_"

            )

        }



    return headers.get(field, data.get("question", "Please answer the question:"))





def format_scheme_results_whatsapp(final_data: dict, language: str = "en") -> str:

    """Formats matched schemes into a clean, comprehensive WhatsApp message."""

    schemes = final_data.get("schemes", [])

    

    if not schemes:

        if language == "hi":

            return "❌ *आपकी जानकारी के अनुसार कोई विशिष्ट योजना नहीं मिली।*\nकृपया अपने स्थानीय कृषि विज्ञान केंद्र (KVK) से संपर्क करें।"

        elif language == "mr":

            return "❌ *तुमच्या माहितीनुसार कोणतीही विशिष्ट योजना आढळली नाही.*\nकृपया तुमच्या स्थानिक कृषी विज्ञान केंद्राशी (KVK) संपर्क साधा."

        elif language == "ta":

            return "❌ *உங்கள் அளவுகோல்களுடன் பொருந்தக்கூடிய திட்டங்கள் எதுவும் இல்லை.*\nஉங்கள் உள்ளூர் வேளாண் அறிவியல் மையத்தை (KVK) அணுகவும்."

        else:

            return "❌ *No specific schemes matched your criteria.*\nPlease check with your local Krishi Vigyan Kendra (KVK)."



    if language == "hi":

        lines = ["🏛️ *संबंधित योजनाएं:*"]

    elif language == "mr":

        lines = ["🏛️ *संबंधित योजना:*"]

    elif language == "ta":

        lines = ["🏛️ *தொடர்புடைய திட்டங்கள்:*"]

    else:

        lines = ["🏛️ *Relevant Schemes:*"]



    for i, s in enumerate(schemes[:5], 1):

        name = s.get("scheme_name") or s.get("short_name")

        url = s.get("official_source", "")

        lines.append(f"*{i}. {name}*")

        if url:

            lines.append(f"   🌐 {url}")

            

    return "\n".join(lines)







def build_whatsapp_interactive_payload(to_number: str, data: dict, language: str = "en") -> Optional[dict]:

    """

    Builds native WhatsApp Cloud API interactive message (List or Button dropdown)

    allowing the user to answer questions using a dropdown list or quick buttons.

    """

    field = data.get("field")

    if not field:

        return None



    ui = _get_ui_strings(field, language)



    if field == "state":

        page = data.get("state_page", 1)

        start_idx = (page - 1) * 7

        remaining_items = ALL_STATES_LIST[start_idx:]

        

        if len(remaining_items) > 8:

            current_items = remaining_items[:7]

            has_more = True

        else:

            current_items = remaining_items

            has_more = False



        rows = [{"id": state, "title": _translate_location(state, "states", language)[:24]} for state in current_items]

        if has_more:

            rows.append({"id": f"more_states_{page + 1}", "title": ui.get("more", "More States ➡️")})

        

        # Always add View All Schemes and End Chat options if there's room

        if len(rows) < 9:

            rows.append({"id": "view_all_schemes", "title": ui.get("all_schemes", "All Govt Schemes")})

        if len(rows) < 10:

            rows.append({"id": "main_menu", "title": ui.get("main_menu", "Main Menu 🏠")})



        return {

            "messaging_product": "whatsapp",

            "to": to_number,

            "type": "interactive",

            "interactive": {

                "type": "list",

                "header": {"type": "text", "text": ui.get("header", "🏛️ Select Your State")},

                "body": {"text": f"Page {page}: Choose your farming state from the menu:"},

                "footer": {"text": ui.get("footer", "KisanGo • All 28 States")},

                "action": {

                    "button": ui.get("button", "Select State ▾"),

                    "sections": [{"title": "States", "rows": rows}]

                }

            }

        }



    if field == "district":

        state_ans = data.get("answers", {}).get("state", "Maharashtra")

        norm = state_ans.lower().strip()

        matched_districts = ["Other"]

        for k, v in STATES_AND_DISTRICTS.items():

            if k.lower() == norm:

                matched_districts = v

                break

                

        page = data.get("district_page", 1)

        start_idx = (page - 1) * 5

        remaining_items = matched_districts[start_idx:]

        

        if len(remaining_items) > 6:

            current_items = remaining_items[:5]

            has_more = True

        else:

            current_items = remaining_items

            has_more = False



        rows = [{"id": dist, "title": _translate_location(dist, "districts", language)[:24]} for dist in current_items]

        if has_more:

            rows.append({"id": f"more_districts_{page + 1}", "title": ui.get("more", "More Districts ➡️")})

        

        # Add Skip option on last page

        if not has_more and "skip" not in [r["id"] for r in rows] and len(rows) < 7:

            rows.append({"id": "skip", "title": ui.get("skip", "Other / Skip ⏭️")})

        

        # Add Schemes and End Chat options if there's room

        if len(rows) < 8:

            rows.append({"id": "view_state_schemes", "title": ui.get("state_schemes", "State Schemes")})

        if len(rows) < 9:

            rows.append({"id": "view_all_schemes", "title": ui.get("all_schemes", "All Govt Schemes")})

        if len(rows) < 10:

            rows.append({"id": "main_menu", "title": ui.get("main_menu", "Main Menu 🏠")})



        return {

            "messaging_product": "whatsapp",

            "to": to_number,

            "type": "interactive",

            "interactive": {

                "type": "list",

                "header": {"type": "text", "text": ui.get("header", "Select District")},

                "body": {"text": f"Page {page}: Choose your district in {state_ans}:"},

                "footer": {"text": ui.get("footer", "KisanGo - Districts")},

                "action": {

                    "button": ui.get("button", "Select District"),

                    "sections": [{"title": "Districts", "rows": rows}]

                }

            }

        }



    if field == "has_insurance":

        return {

            "messaging_product": "whatsapp",

            "to": to_number,

            "type": "interactive",

            "interactive": {

                "type": "list",

                "header": {"type": "text", "text": ui.get("header", "Crop Insurance (PMFBY)")},

                "body": {"text": "Do you currently have crop insurance under PMFBY?"},

                "footer": {"text": ui.get("footer", "KisanGo - Scheme Check")},

                "action": {

                    "button": ui.get("button", "Select Answer"),

                    "sections": [{

                        "title": "Options",

                        "rows": [

                            {"id": "yes", "title": ui.get("yes", "Yes - I have insurance")},

                            {"id": "no", "title": ui.get("no", "No - I don't have it")},

                            {"id": "skip", "title": ui.get("skip", "Not Sure / Skip")},

                            {"id": "view_state_schemes", "title": ui.get("state_schemes", "State Schemes")},

                            {"id": "view_all_schemes", "title": ui.get("all_schemes", "All Govt Schemes")},

                            {"id": "main_menu", "title": ui.get("main_menu", "Main Menu 🏠")}

                        ]

                    }]

                }

            }

        }

    if field == "crop":
        return {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": data.get("question", "Enter Crop Name / Send a photo")},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": "skip", "title": ui.get("skip", "Skip / No Crop ⏭️")[:20]}},
                        {"type": "reply", "reply": {"id": "view_all_schemes", "title": ui.get("all_schemes", "All Schemes")[:20]}},
                        {"type": "reply", "reply": {"id": "main_menu", "title": ui.get("main_menu", "Main Menu 🏠")[:20]}}
                    ]
                }
            }
        }

    if field == "damage_pct":

        levels = ui.get("levels", ["10% - 20%", "20% - 33%", "33% - 50%", "50% - 75%", "75% - 100%"])

        desc = ui.get("desc", ["Minor pest/disease damage", "Moderate crop damage", "Significant disaster loss", "Severe crop damage", "Total crop loss"])

        return {

            "messaging_product": "whatsapp",

            "to": to_number,

            "type": "interactive",

            "interactive": {

                "type": "list",

                "header": {"type": "text", "text": ui.get("header", "Crop Damage Level")},

                "body": {"text": "Please select your estimated crop damage level:"},

                "footer": {"text": ui.get("footer", "Used to check Calamity Relief threshold")},

                "action": {

                    "button": ui.get("button", "Select Damage %"),

                    "sections": [

                        {

                            "title": "Damage Levels",

                            "rows": [

                                {"id": "15%", "title": levels[0], "description": desc[0]},

                                {"id": "30%", "title": levels[1], "description": desc[1]},

                                {"id": "40%", "title": levels[2], "description": desc[2]},

                                {"id": "65%", "title": levels[3], "description": desc[3]},

                                {"id": "90%", "title": levels[4], "description": desc[4]},

                                {"id": "skip", "title": ui.get("skip", "Not Sure / Skip")},

                                {"id": "view_state_schemes", "title": ui.get("state_schemes", "State Schemes")},

                                {"id": "view_all_schemes", "title": ui.get("all_schemes", "All Govt Schemes")},

                                {"id": "main_menu", "title": ui.get("main_menu", "Main Menu 🏠")}

                            ]

                        }

                    ]

                }

            }

        }



    if field == "farmer_category":

        titles = ui.get("titles", ["Small & Marginal", "Medium Farmer", "Large Farmer", "Tenant Farmer"])

        desc = ui.get("desc", ["Under 2 Hectares (5 Acres)", "2 to 10 Hectares", "Above 10 Hectares", "Sharecropper or tenant"])

        return {

            "messaging_product": "whatsapp",

            "to": to_number,

            "type": "interactive",

            "interactive": {

                "type": "list",

                "header": {"type": "text", "text": ui.get("header", "Farmer Category")},

                "body": {"text": "Please select your landholding category:"},

                "footer": {"text": ui.get("footer", "Small/marginal farmers receive higher subsidies")},

                "action": {

                    "button": ui.get("button", "Select Category"),

                    "sections": [

                        {

                            "title": "Landholding Categories",

                            "rows": [

                                {"id": "Small/Marginal", "title": titles[0], "description": desc[0]},

                                {"id": "Medium", "title": titles[1], "description": desc[1]},

                                {"id": "Large", "title": titles[2], "description": desc[2]},

                                {"id": "Tenant", "title": titles[3], "description": desc[3]},

                                {"id": "skip", "title": ui.get("skip", "Skip / General"), "description": ui.get("skip_desc", "Skip this step")},

                                {"id": "view_state_schemes", "title": ui.get("state_schemes", "State Schemes")},

                                {"id": "view_all_schemes", "title": ui.get("all_schemes", "All Govt Schemes")},

                                {"id": "main_menu", "title": ui.get("main_menu", "Main Menu 🏠")}

                            ]

                        }

                    ]

                }

            }

        }



    return None



