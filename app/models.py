from enum import Enum
from typing import List
from pydantic import BaseModel, field_validator


class PriorityLevel(str, Enum):
    CODE_RED = "CODE_RED"
    CODE_ORANGE = "CODE_ORANGE"
    CODE_GREEN = "CODE_GREEN"


class IncidentMetadata(BaseModel):
    priority_level: PriorityLevel
    confidence_score: float

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("confidence_score must be between 0.0 and 1.0")
        return v


class ExtractedMedicalEntities(BaseModel):
    suspected_primary_condition: str
    respiratory_estimate: str
    consciousness_level: str


class DispatchRecommendation(BaseModel):
    required_specialists: List[str]
    equipment_loadout: List[str]


class TriageReport(BaseModel):
    incident_metadata: IncidentMetadata
    extracted_medical_entities: ExtractedMedicalEntities
    environmental_hazards: List[str]
    dispatch_recommendation: DispatchRecommendation
    requires_human_verification: bool = False

    def check_verification_needed(self) -> None:
        if self.incident_metadata.confidence_score < 0.85:
            self.requires_human_verification = True
