from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, field_validator


class PriorityLevel(str, Enum):
    CODE_RED = "CODE_RED"
    CODE_ORANGE = "CODE_ORANGE"
    CODE_GREEN = "CODE_GREEN"


class IncidentMetadata(BaseModel):
    priority_level: PriorityLevel
    confidence_score: float
    estimated_victims: int = 0
    location_description: Optional[str] = None

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("confidence_score must be between 0.0 and 1.0")
        return v


class ExtractedMedicalEntities(BaseModel):
    suspected_primary_condition: Optional[str] = "Not applicable"
    respiratory_estimate: Optional[str] = "Not applicable"
    consciousness_level: Optional[str] = "Not applicable"


class DispatchRecommendation(BaseModel):
    required_specialists: List[str]
    equipment_loadout: List[str]
    nearest_hospital: Optional[str] = None
    nearest_fire_station: Optional[str] = None
    nearest_hydrant: Optional[str] = None


class ScamAssessment(BaseModel):
    gemini_scam_score: float = 0.0
    nlp_scam_score: float = 0.0
    final_scam_probability: float = 0.0
    is_suspected_scam: bool = False
    scam_indicators: List[str] = []

    @field_validator("gemini_scam_score", "nlp_scam_score", "final_scam_probability")
    @classmethod
    def validate_scores(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("Score must be between 0.0 and 1.0")
        return v


class TrafficRoute(BaseModel):
    travel_time_minutes: int = 0
    distance_km: float = 0.0
    traffic_condition: str = "Calculating..."
    traffic_delay_minutes: int = 0


class HospitalAlert(BaseModel):
    name: str = "Unknown"
    city: str = "Unknown"
    distance_km: float = 0.0
    available_bays: int = 0
    surgeons_on_call: List[str] = []
    equipment: List[str] = []
    eta_minutes: int = 0
    preparation_instructions: Optional[str] = None
    traffic_route: TrafficRoute = TrafficRoute()


class PriorityQueue(BaseModel):
    queue_position: int = 1
    total_active_incidents: int = 1
    ambulances_available: int = 3
    priority_reason: str = "Single incident"


class TriageReport(BaseModel):
    incident_metadata: IncidentMetadata
    extracted_medical_entities: ExtractedMedicalEntities
    environmental_hazards: List[str]
    dispatch_recommendation: DispatchRecommendation
    scam_assessment: ScamAssessment = ScamAssessment()
    hospital_alert: HospitalAlert = HospitalAlert()
    priority_queue: PriorityQueue = PriorityQueue()
    requires_human_verification: bool = False

    def check_verification_needed(self) -> None:
        if self.incident_metadata.confidence_score < 0.85:
            self.requires_human_verification = True
        if self.scam_assessment.final_scam_probability > 0.7:
            self.requires_human_verification = True