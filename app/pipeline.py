import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from transformers import pipeline as hf_pipeline
import google.generativeai as genai
import json
import time
from dotenv import load_dotenv
from app.models import TriageReport, ScamAssessment, IncidentMetadata, ExtractedMedicalEntities, DispatchRecommendation

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path=dotenv_path, override=True)

SYSTEM_PROMPT = """
You are a medical triage AI assistant for emergency services.
Analyze the provided emergency scene video and audio, then return ONLY a valid JSON object.
No explanations. No markdown. No extra text. Just the JSON.

The JSON must follow this exact structure:
{
    "incident_metadata": {
        "priority_level": "CODE_RED" | "CODE_ORANGE" | "CODE_GREEN",
        "confidence_score": float between 0.0 and 1.0,
        "estimated_victims": integer,
        "location_description": string or null
    },
    "extracted_medical_entities": {
        "suspected_primary_condition": string,
        "respiratory_estimate": string,
        "consciousness_level": string
    },
    "environmental_hazards": [list of strings],
    "dispatch_recommendation": {
        "required_specialists": [list of strings],
        "equipment_loadout": [list of strings],
        "nearest_hospital": null,
        "nearest_fire_station": null,
        "nearest_hydrant": null
    },
    "scam_assessment": {
        "gemini_scam_score": float between 0.0 and 1.0,
        "nlp_scam_score": 0.0,
        "final_scam_probability": float between 0.0 and 1.0,
        "is_suspected_scam": boolean,
        "scam_indicators": [list of strings]
    }
}

Rules:
- confidence_score below 0.85 means insufficient visual/audio data
- estimated_victims: count visible people involved in the incident
- location_description: extract from audio if caller mentions location, otherwise null
- gemini_scam_score: assess if this appears to be a false/prank call (0.0 = genuine, 1.0 = scam)
- scam_indicators: list specific reasons if scam suspected (e.g. "caller laughing", "no visible incident")
- nlp_scam_score and final_scam_probability: set same as gemini_scam_score for now
- Be conservative — if unsure, lower the confidence score
- Never invent injuries you cannot observe or hear
- environmental_hazards can be empty list if none detected
- nearest_hospital, nearest_fire_station, nearest_hydrant: always null (populated by routing layer)
"""

# Initialize once at module level
scam_classifier = hf_pipeline(
    "zero-shot-classification",
    model="facebook/bart-large-mnli"
)

def detect_scam_nlp(transcript: str) -> float:
    if not transcript or len(transcript.strip()) < 10:
        return 0.0

    result = scam_classifier(
        transcript,
        candidate_labels=["genuine emergency call", "false alarm", "prank call"]
    )

    labels = result["labels"]
    scores = result["scores"]
    label_score_map = dict(zip(labels, scores))

    scam_score = (
        label_score_map.get("false alarm", 0.0) +
        label_score_map.get("prank call", 0.0)
    )

    return round(min(scam_score, 1.0), 3)


def analyze_emergency_scene(video_path: str) -> TriageReport:
    model = genai.GenerativeModel("gemini-2.5-flash")

    print("Uploading video to Gemini...")
    video_file = genai.upload_file(video_path)

    print("Waiting for file to process...")
    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = genai.get_file(video_file.name)
        print(f"File state: {video_file.state.name}")

    if video_file.state.name == "FAILED":
        raise ValueError("Video processing failed")

    print("Analyzing scene...")
    response = model.generate_content(
        [video_file, SYSTEM_PROMPT],
        generation_config=genai.GenerationConfig(
            temperature=0.0,
            max_output_tokens=2048,
        )
    )

    raw_text = response.text.strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    print(f"Gemini response: {raw_text}")

    raw_json = json.loads(raw_text)
    report = TriageReport(**raw_json)

    # EARLY SCAM EXIT
    if report.scam_assessment.gemini_scam_score >= 0.85:
        return TriageReport(
            incident_metadata=IncidentMetadata(
                priority_level="CODE_GREEN",
                confidence_score=1.0,
                estimated_victims=0,
                location_description="TRACE REQUIRED"
            ),
            extracted_medical_entities=ExtractedMedicalEntities(
                suspected_primary_condition="SCAM CALL DETECTED - DO NOT DISPATCH",
                respiratory_estimate="N/A",
                consciousness_level="N/A"
            ),
            environmental_hazards=[],
            dispatch_recommendation=DispatchRecommendation(
                required_specialists=["Law Enforcement - False Alarm Protocol"],
                equipment_loadout=[]
            ),
            scam_assessment=ScamAssessment(
                gemini_scam_score=report.scam_assessment.gemini_scam_score,
                nlp_scam_score=0.0,
                final_scam_probability=report.scam_assessment.gemini_scam_score,
                is_suspected_scam=True,
                scam_indicators=report.scam_assessment.scam_indicators
            ),
            requires_human_verification=True
        )

    # Genuine call — run NLP scam detector
    transcript = report.incident_metadata.location_description or ""
    nlp_score = detect_scam_nlp(transcript)

    report.scam_assessment.nlp_scam_score = nlp_score
    report.scam_assessment.final_scam_probability = round(
        (report.scam_assessment.gemini_scam_score + nlp_score) / 2, 3
    )
    report.scam_assessment.is_suspected_scam = (
        report.scam_assessment.final_scam_probability > 0.7
    )

    report.check_verification_needed()

    return report