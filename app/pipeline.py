import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import google.generativeai as genai
import json
from dotenv import load_dotenv
from app.models import TriageReport

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

SYSTEM_PROMPT = """
You are a medical triage AI assistant for emergency services.
Analyze the provided emergency scene video and return ONLY a valid JSON object.
No explanations. No markdown. No extra text. Just the JSON.

The JSON must follow this exact structure:
{
    "incident_metadata": {
        "priority_level": "CODE_RED" | "CODE_ORANGE" | "CODE_GREEN",
        "confidence_score": float between 0.0 and 1.0
    },
    "extracted_medical_entities": {
        "suspected_primary_condition": string,
        "respiratory_estimate": string,
        "consciousness_level": string
    },
    "environmental_hazards": [list of strings],
    "dispatch_recommendation": {
        "required_specialists": [list of strings],
        "equipment_loadout": [list of strings]
    }
}

Rules:
- confidence_score below 0.85 means insufficient visual/audio data
- Be conservative — if unsure, lower the confidence score
- Never invent injuries you cannot observe or hear
- environmental_hazards can be empty list if none detected
"""

def analyze_emergency_scene(video_path: str) -> TriageReport:
    """
    Takes a video file path, sends to Gemini, returns validated TriageReport
    """
    model = genai.GenerativeModel("gemini-2.0-flash")

    # Upload video to Gemini
    print("Uploading video to Gemini...")
    video_file = genai.upload_file(video_path)

    # Single API call — genuine multimodal
    print("Analyzing scene...")
    response = model.generate_content(
        [video_file, SYSTEM_PROMPT],
        generation_config=genai.GenerationConfig(
            temperature=0.0,  # Deterministic output
            max_output_tokens=1024,
        )
    )

    # Parse and validate through Pydantic
    raw_json = json.loads(response.text)
    report = TriageReport(**raw_json)
    report.check_verification_needed()

    return report