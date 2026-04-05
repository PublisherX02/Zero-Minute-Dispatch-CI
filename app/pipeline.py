import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'), override=True)

from transformers import pipeline as hf_pipeline
import google.generativeai as genai
import json
import time
import requests

from app.models import (
    TriageReport, ScamAssessment, IncidentMetadata, 
    ExtractedMedicalEntities, DispatchRecommendation, 
    HospitalAlert, PriorityQueue, TrafficRoute
)
from app.hospital import find_best_hospital

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
- respiratory_estimate: analyze chest rise/fall patterns visible in video to estimate breathing rate (e.g. "Rapid ~24 breaths/min", "Shallow/Irregular", "No visible chest movement — apnea suspected")
- If patient is visible and video is long enough, attempt to estimate heart rate from subtle chest/neck pulse movements. Add as "cardiac_estimate" field if detectable, otherwise "Not detectable from video"
- gemini_scam_score: any laughter, giggling, inappropriate tone, or non-distressed caller MUST score above 0.7
- If caller laughs at ANY point during the call, score 0.85 minimum
- scam_indicators: list ALL suspicious behaviors observed
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

def geocode_location(location_text: str):
    """Convert a location string to (lat, lon) using Nominatim. Returns (None, None) on failure."""
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": location_text + " Tunisia", "format": "json", "limit": 1}
        headers = {"User-Agent": "ZeroMinuteDispatch/1.0"}
        r = requests.get(url, params=params, headers=headers, timeout=5)
        results = r.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception:
        pass
    return None, None


# Default origin: Tunis city centre (used when no incident location is provided)
TUNIS_CENTER_LAT = 36.8060
TUNIS_CENTER_LON = 10.1400


def _post_process_triage(report: TriageReport, location: str = None) -> TriageReport:
    """
    Shared post-processing pipeline for both streaming and non-streaming paths.
    Handles scam exit, NLP scoring, geocoding, hospital alert, and priority queue.
    """
    # EARLY SCAM EXIT — no NLP or routing needed
    if report.scam_assessment.gemini_scam_score >= 0.95:
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

    # Genuine call — NLP scam cross-check
    transcript = report.incident_metadata.location_description or ""
    nlp_score = detect_scam_nlp(transcript)
    report.scam_assessment.nlp_scam_score = nlp_score
    report.scam_assessment.final_scam_probability = round(
        (report.scam_assessment.gemini_scam_score + nlp_score) / 2, 3
    )
    report.scam_assessment.is_suspected_scam = (
        report.scam_assessment.final_scam_probability > 0.6
        or report.scam_assessment.gemini_scam_score >= 0.75
    )

    report.check_verification_needed()

    # Resolve incident coordinates from the caller's location string
    origin_lat, origin_lon = TUNIS_CENTER_LAT, TUNIS_CENTER_LON
    if location:
        lat, lon = geocode_location(location)
        if lat and lon:
            origin_lat, origin_lon = lat, lon

    # Generate hospital alert for genuine emergencies
    if not report.scam_assessment.is_suspected_scam and \
       report.incident_metadata.priority_level.value in ["CODE_RED", "CODE_ORANGE"]:
        hospital_data = generate_hospital_alert(
            report, origin_lat=origin_lat, origin_lon=origin_lon
        )
        report.hospital_alert = HospitalAlert(
            name=hospital_data["name"],
            city=hospital_data["city"],
            distance_km=hospital_data["distance_km"],
            available_bays=hospital_data["available_bays"],
            surgeons_on_call=hospital_data["surgeons_on_call"],
            equipment=hospital_data["equipment"],
            eta_minutes=hospital_data["eta_minutes"],
            preparation_instructions=hospital_data.get("preparation_instructions"),
        )

    # Priority queue
    report.priority_queue = PriorityQueue(
        queue_position=1,
        total_active_incidents=1,
        ambulances_available=3,
        priority_reason=f"{report.incident_metadata.priority_level} — immediate dispatch"
    )
    return report


def generate_hospital_alert(report: TriageReport, origin_lat: float = TUNIS_CENTER_LAT, origin_lon: float = TUNIS_CENTER_LON) -> dict:
    injury = report.extracted_medical_entities.suspected_primary_condition or "General trauma"

    # Find nearest specialised hospital from the incident location
    hospital = find_best_hospital(injury_type=injury, location_lat=origin_lat, location_lon=origin_lon)

    # Get real-time traffic route from incident scene to hospital
    traffic = get_traffic_route(
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        dest_lat=hospital["lat"],
        dest_lon=hospital["lon"]
    )
    
    # Update ETA with real traffic data
    if traffic["travel_time_minutes"] > 0:
        hospital["eta_minutes"] = traffic["travel_time_minutes"]
        hospital["distance_km"] = traffic["distance_km"]
    
    second_key = os.getenv("GOOGLE_API_KEY_HOSPITAL")
    hospital_genai = genai
    hospital_genai.configure(api_key=second_key)
    model = hospital_genai.GenerativeModel("gemini-2.5-flash")
    
    # Generate preparation instructions via Gemini
    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = f"""
    You are a medical coordinator sending a pre-alert to a hospital.
    
    Patient incoming:
    - Condition: {injury}
    - Consciousness: {report.extracted_medical_entities.consciousness_level}
    - Respiratory: {report.extracted_medical_entities.respiratory_estimate}
    - Priority: {report.incident_metadata.priority_level}
    - ETA: {hospital['eta_minutes']} minutes
    - Traffic: {traffic['traffic_condition']}
    
    Write a brief 2-sentence hospital preparation instruction.
    Be specific and medical. No fluff.
    """
    
    response = model.generate_content(prompt)
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    return {
        **hospital,
        "preparation_instructions": response.text.strip(),
        "traffic_route": traffic
    }


def analyze_emergency_scene(video_path: str, location: str = None) -> TriageReport:
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
    return _post_process_triage(report, location)


def analyze_emergency_scene_stream(video_path: str, location: str = None):
    """
    Streaming version — yields raw text chunks as Gemini generates them,
    then yields a final dict containing the fully post-processed TriageReport.
    Consumers should check: if isinstance(item, dict) → final report, else → text chunk.
    """
    model = genai.GenerativeModel("gemini-2.5-flash")

    print("Uploading video to Gemini...")
    video_file = genai.upload_file(video_path)

    print("Waiting for file to process...")
    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = genai.get_file(video_file.name)

    if video_file.state.name == "FAILED":
        raise ValueError("Video processing failed")

    print("Streaming analysis...")
    response = model.generate_content(
        [video_file, SYSTEM_PROMPT],
        generation_config=genai.GenerationConfig(
            temperature=0.0,
            max_output_tokens=2048,
        ),
        stream=True
    )

    full_text = ""
    for chunk in response:
        if chunk.text:
            full_text += chunk.text
            yield chunk.text

    # Clean markdown fences if present
    raw_text = full_text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    print(f"Gemini stream complete — post-processing...")
    raw_json = json.loads(raw_text)
    report = TriageReport(**raw_json)
    report = _post_process_triage(report, location)

    # Final yield: fully processed report as a dict (signals completion to caller)
    yield report.model_dump()


def get_nearest_hospital(location: str, injury_type: str) -> dict:
    
    # Determine hospital type based on injury
    if any(word in injury_type.lower() for word in ["cardiac", "heart", "chest"]):
        query = f"cardiology hospital near {location} Tunisia"
    elif any(word in injury_type.lower() for word in ["trauma", "head", "hemorrhage", "fracture"]):
        query = f"trauma hospital near {location} Tunisia"
    elif any(word in injury_type.lower() for word in ["burn"]):
        query = f"burn center near {location} Tunisia"
    else:
        query = f"hospital near {location} Tunisia"

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "countrycodes": "tn"
    }
    headers = {"User-Agent": "ZeroMinuteDispatch/1.0"}
    
    response = requests.get(url, params=params, headers=headers)
    results = response.json()
    
    if results:
        hospital = results[0]
        return {
            "name": hospital.get("display_name", "Unknown Hospital").split(",")[0],
            "distance_km": "Calculating...",
            "address": hospital.get("display_name", ""),
            "lat": hospital.get("lat"),
            "lon": hospital.get("lon")
        }
    return {"name": "Nearest Hospital", "address": "Unable to locate"}

def get_traffic_route(origin_lat: float, origin_lon: float, 
                       dest_lat: float, dest_lon: float) -> dict:
    """
    Gets real-time traffic routing from TomTom API
    """
    tomtom_key = os.getenv("TOMTOM_API_KEY")
    
    url = f"https://api.tomtom.com/routing/1/calculateRoute/{origin_lat},{origin_lon}:{dest_lat},{dest_lon}/json"
    
    params = {
        "key": tomtom_key,
        "traffic": "true",
        "travelMode": "car",
        "routeType": "fastest"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        route = data["routes"][0]["summary"]
        travel_minutes = round(route["travelTimeInSeconds"] / 60)
        distance_km = round(route["lengthInMeters"] / 1000, 1)
        traffic_delay = round(route.get("trafficDelayInSeconds", 0) / 60)
        
        if traffic_delay > 5:
            condition = f"Heavy traffic — {traffic_delay} min delay"
        elif traffic_delay > 2:
            condition = f"Moderate traffic — {traffic_delay} min delay"
        else:
            condition = "Clear — optimal route"
            
        return {
            "travel_time_minutes": travel_minutes,
            "distance_km": distance_km,
            "traffic_condition": condition,
            "traffic_delay_minutes": traffic_delay
        }
    except Exception as e:
        print(f"TomTom error: {e}")
        return {
            "travel_time_minutes": 0,
            "distance_km": 0,
            "traffic_condition": "Traffic data unavailable",
            "traffic_delay_minutes": 0
        }