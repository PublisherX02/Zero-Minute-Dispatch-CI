import pytest
from pydantic import BaseModel, Field
from typing import List
from enum import Enum

# --- Your Pydantic Models ---

class PriorityLevel(str, Enum):
    CODE_RED = "CODE_RED"
    CODE_ORANGE = "CODE_ORANGE"
    CODE_GREEN = "CODE_GREEN"

class IncidentMetadata(BaseModel):
    priority_level: PriorityLevel
    confidence_score: float = Field(..., ge=0.0, le=1.0)

class MedicalEntities(BaseModel):
    suspected_primary_condition: str
    respiratory_estimate: str
    consciousness_level: str

class DispatchRecommendation(BaseModel):
    required_specialists: List[str]
    equipment_loadout: List[str]

class TriageReport(BaseModel):
    incident_metadata: IncidentMetadata
    extracted_medical_entities: MedicalEntities
    environmental_hazards: List[str]
    dispatch_recommendation: DispatchRecommendation
    human_verification_required: bool = False

    def check_verification_needed(self):
        if self.incident_metadata.confidence_score < 0.85:
            self.human_verification_required = True
        return self


# --- The Tests ---

def test_valid_triage_report():
    """A complete valid report should pass validation"""
    report = TriageReport(
        incident_metadata={
            "priority_level": "CODE_RED",
            "confidence_score": 0.92
        },
        extracted_medical_entities={
            "suspected_primary_condition": "Severe Hemorrhage",
            "respiratory_estimate": "Rapid / Shallow",
            "consciousness_level": "Unresponsive"
        },
        environmental_hazards=["Fire risk", "Unstable vehicle"],
        dispatch_recommendation={
            "required_specialists": ["Trauma Surgeon"],
            "equipment_loadout": ["Tourniquet", "O-Negative Blood"]
        }
    )
    assert report.incident_metadata.priority_level == PriorityLevel.CODE_RED
    assert report.incident_metadata.confidence_score == 0.92


def test_invalid_confidence_score():
    """Confidence score above 1.0 should fail"""
    with pytest.raises(Exception):
        TriageReport(
            incident_metadata={
                "priority_level": "CODE_RED",
                "confidence_score": 1.5
            },
            extracted_medical_entities={
                "suspected_primary_condition": "Unknown",
                "respiratory_estimate": "Unknown",
                "consciousness_level": "Unknown"
            },
            environmental_hazards=[],
            dispatch_recommendation={
                "required_specialists": [],
                "equipment_loadout": []
            }
        )


def test_human_verification_flag():
    """Low confidence score should trigger human verification"""
    report = TriageReport(
        incident_metadata={
            "priority_level": "CODE_ORANGE",
            "confidence_score": 0.72
        },
        extracted_medical_entities={
            "suspected_primary_condition": "Unknown Trauma",
            "respiratory_estimate": "Unknown",
            "consciousness_level": "Unclear"
        },
        environmental_hazards=[],
        dispatch_recommendation={
            "required_specialists": [],
            "equipment_loadout": []
        }
    )
    report.check_verification_needed()
    assert report.human_verification_required == True