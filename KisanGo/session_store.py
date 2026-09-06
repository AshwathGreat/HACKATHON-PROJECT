from datetime import datetime
from typing import Dict, List, Optional
from models import CropDiagnosis, ChatMessage
import services.scheme_conversation as scheme_conv


class FarmerSession:
    def __init__(self, session_id: str):
        self.session_id: str = session_id
        self.last_diagnosis: Optional[CropDiagnosis] = None
        self.language: str = "en"
        self.messages: List[ChatMessage] = []
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()
        self.scheme_session_id: Optional[str] = None
        self.last_scheme_step: Optional[dict] = None
        self.last_known_state: Optional[str] = None  # Remembered from scheme flow

    def add_message(self, role: str, content: str, image_url: Optional[str] = None):
        self.messages.append(
            ChatMessage(
                role=role,
                content=content,
                image_url=image_url,
                timestamp=datetime.now().strftime("%H:%M")
            )
        )
        self.updated_at = datetime.now()

    def set_diagnosis(self, diagnosis: CropDiagnosis, image_url: Optional[str] = None):
        self.last_diagnosis = diagnosis
        self.add_message(
            role="assistant",
            content=diagnosis.farmer_friendly_summary,
            image_url=image_url
        )

    def start_scheme_flow(self, language: Optional[str] = None, prefill: Optional[dict] = None) -> dict:
        """Starts a conversational scheme eligibility check session."""
        lang = language or self.language
        res = scheme_conv.start_session(language=lang, prefill=prefill)
        self.scheme_session_id = res.get("session_id")
        self.last_scheme_step = res if not res.get("done") else None
        return res

    def answer_scheme_flow(self, answer: str) -> dict:
        """Submits an answer to the ongoing scheme flow."""
        if not self.scheme_session_id:
            return {"done": True, "error": "No active scheme session"}
        res = scheme_conv.answer_session(self.scheme_session_id, answer)
        if res.get("done") or res.get("error"):
            # Save the state the user answered so we can use it for future photo diagnoses
            if res.get("answers_given"):
                state = res["answers_given"].get("state")
                if state:
                    self.last_known_state = state
            self.scheme_session_id = None
            self.last_scheme_step = None
        else:
            # Track state as soon as it's answered (in the answers dict)
            answers = res.get("answers", {})
            if answers.get("state"):
                self.last_known_state = answers["state"]
            self.last_scheme_step = res
        return res

    def clear_scheme_flow(self):
        """Cancels or resets any ongoing scheme questionnaire."""
        self.scheme_session_id = None
        self.last_scheme_step = None

    def has_active_scheme_flow(self) -> bool:
        """Returns True if the farmer is currently in a step-by-step scheme question flow."""
        return bool(self.scheme_session_id)


class SessionManager:
    """Manages active chat sessions by phone number (for WhatsApp) or session ID (for web simulator)."""

    def __init__(self):
        self._sessions: Dict[str, FarmerSession] = {}

    def get_or_create(self, session_id: str) -> FarmerSession:
        clean_id = session_id.strip()
        if clean_id not in self._sessions:
            self._sessions[clean_id] = FarmerSession(clean_id)
        return self._sessions[clean_id]

    def get(self, session_id: str) -> Optional[FarmerSession]:
        return self._sessions.get(session_id.strip())

    def update_diagnosis(self, session_id: str, diagnosis: CropDiagnosis, image_url: Optional[str] = None) -> FarmerSession:
        session = self.get_or_create(session_id)
        session.set_diagnosis(diagnosis, image_url=image_url)
        return session

    def set_language(self, session_id: str, language: str) -> FarmerSession:
        session = self.get_or_create(session_id)
        session.language = language
        return session

    def clear(self, session_id: str):
        if session_id in self._sessions:
            del self._sessions[session_id]


# Singleton instance
session_manager = SessionManager()
