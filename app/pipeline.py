import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import google.generativeai as genai
import json
import time
from dotenv import load_dotenv
from app.models import TriageReport

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

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

def analyze_emergency_scene(video_path: str) -> TriageReport:
    """
    Takes a video file path, sends to Gemini, returns validated TriageReport
    """
    model = genai.GenerativeModel("gemini-2.5-flash")

    # Upload video to Gemini
    print("Uploading video to Gemini...")
    video_file = genai.upload_file(video_path)

    # Wait for file to become ACTIVE
    print("Waiting for file to process...")
    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = genai.get_file(video_file.name)
        print(f"File state: {video_file.state.name}")

    if video_file.state.name == "FAILED":
        raise ValueError("Video processing failed")

    # Single API call — genuine multimodal
    print("Analyzing scene...")
    response = model.generate_content(
        [video_file, SYSTEM_PROMPT],
        generation_config=genai.GenerationConfig(
            temperature=0.0,
            max_output_tokens=2048,
        )
    )

    # Clean response — remove markdown if present
    raw_text = response.text.strip()
    
    # Remove markdown code blocks if Gemini wrapped the JSON
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    # Print so we can see what Gemini returned
    print(f"Gemini response: {raw_text}")

    # Parse and validate through Pydantic
    raw_json = json.loads(raw_text)
    report = TriageReport(**raw_json)
    report.check_verification_needed()

    return report