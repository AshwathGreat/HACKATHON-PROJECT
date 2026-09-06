from typing import List, Optional
from pydantic import BaseModel, Field


class TreatmentPlan(BaseModel):
    """Detailed treatment breakdown divided into organic, chemical, and cultural."""
    organic: List[str] = Field(
        default_factory=list,
        description="Bio-fungicides, neem oil, organic sprays, biological agents, or organic amendments."
    )
    chemical: List[str] = Field(
        default_factory=list,
        description="Recommended chemical fungicides, bactericides, insecticides, or fertilizers with specific dosage guidelines and safety notes."
    )
    cultural: List[str] = Field(
        default_factory=list,
        description="Farming practices, e.g. pruning infected foliage, improving drainage, spacing, sanitation, or crop rotation."
    )


class CropDiagnosis(BaseModel):
    """Comprehensive agricultural diagnostic report from multimodal AI."""
    is_crop: bool = Field(
        description="True if the image contains a plant, crop, leaf, stem, fruit, vegetable, flower, or farm field. False if it's unrelated (e.g. human face, vehicle, animal, indoor object, blurred mess)."
    )
    crop_name: str = Field(
        default="Unknown",
        description="Common name of the crop or plant (e.g. Tomato, Rice/Paddy, Wheat, Potato, Maize/Corn, Cotton, Sugarcane, Chili, Banana, etc.)."
    )
    is_healthy: bool = Field(
        default=False,
        description="True if the crop is healthy and exhibits no significant disease, pest attack, or severe nutritional deficiency."
    )
    condition_name: str = Field(
        default="Healthy Crop",
        description="Primary diagnosis: disease name, pest infestation, nutrient deficiency, or 'Healthy Crop' if healthy."
    )
    scientific_name: Optional[str] = Field(
        default=None,
        description="Scientific name of pathogen, pest, or crop if identifiable (e.g., 'Alternaria solani', 'Magnaporthe oryzae')."
    )
    severity: str = Field(
        default="N/A",
        description="Severity level of the condition: 'Healthy', 'Mild', 'Moderate', 'Severe', or 'Critical'."
    )
    confidence_score: float = Field(
        default=0.9,
        description="Confidence score between 0.0 and 1.0 of the diagnosis."
    )
    symptoms_detected: List[str] = Field(
        default_factory=list,
        description="Specific visual symptoms spotted on the leaf, fruit, or stem (e.g., 'concentric brown rings with yellow halo', 'powdery white fungal patches')."
    )
    causes: List[str] = Field(
        default_factory=list,
        description="Underlying causes such as fungal spores, high humidity, aphids, poor air circulation, or nitrogen deficiency."
    )
    treatment: TreatmentPlan = Field(
        default_factory=TreatmentPlan,
        description="Actionable treatment options for the farmer."
    )
    preventive_measures: List[str] = Field(
        default_factory=list,
        description="Preventive measures to safeguard the remaining crop and future seasons."
    )
    farmer_friendly_summary: str = Field(
        description="Ready-to-send WhatsApp message formatted with markdown (*bold*, bullets) and emojis, easy for a farmer to read and act upon immediately."
    )


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    image_url: Optional[str] = None
    timestamp: Optional[str] = None


class TextQueryRequest(BaseModel):
    session_id: str
    message: str
    language: Optional[str] = "en"
