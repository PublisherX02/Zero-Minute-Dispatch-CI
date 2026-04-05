# Zero-Minute Dispatch
[![Zero-Minute Dispatch CI](https://github.com/PublisherX02/Zero-Minute-Dispatch-CI/actions/workflows/ci.yml/badge.svg)](https://github.com/PublisherX02/Zero-Minute-Dispatch-CI/actions/workflows/ci.yml)

> **Eliminating the "Blind Arrival" in Emergency Medical Response**

Built for **Humanovators 2.0 Hackathon** — Theme: Smart Mobility for Healthcare  
Challenge Area: Dynamic Vehicle Routing for Emergency Medical Services (EMS)

> Validated through direct field interviews with Civil Protection Officials and Emergency Medical Doctors — Tunisia, April 2026

---

## The Problem: The Blind Arrival

When a bystander calls 198 (Tunisia's emergency number), the information passed through the chain is chaotic, incomplete, and manual.

```
Bystander (panicked, unclear)
    ↓  phone call
Dispatcher (verbal summary only)
    ↓  brief handwritten note
Paramedic crew (no structured data)
    ↓  arrive at scene
BLIND ARRIVAL — wrong equipment, wrong specialists, wasted Golden Hour minutes
```

Field interviews identified four specific gaps:

| Gap | Current Reality | Impact |
|---|---|---|
| Victim count | Dispatcher estimate only | Wrong resources dispatched |
| Injury type | Verbal description | Wrong equipment loaded |
| False calls | No validation | ~15% of dispatches wasted |
| Hospital readiness | No pre-alert | ER unprepared on arrival |

---

## The Solution

Zero-Minute Dispatch is an AI triage pipeline that sits between the emergency call and the ambulance crew. It ingests the raw scene video or audio, produces a structured medical intelligence report, and transmits it to the crew and the receiving hospital — before the ambulance reaches the scene.

```
Scene video / audio
        ↓
  Gemini 2.5 Flash  ──────────────────────────────────────────────────────┐
  (multimodal analysis)                                                   │
        ↓                                                                 │
  BART-large-mnli                                               Streaming SSE
  (NLP scam cross-check)                                       (live to dashboard)
        ↓                                                                 │
  Ensemble decision                                                       │
  (genuine / scam)                                                        │
        ↓                                                                 │
  Pydantic validation ◄───────────────────────────────────────────────────┘
        ↓
  ┌─────────────────┬──────────────────┐
  │                 │                  │
  ▼                 ▼                  ▼
Hospital       TomTom routing     Priority queue
pre-alert      (real road ETA)    assignment
  │                 │                  │
  └─────────────────┴──────────────────┘
                    ↓
        Ops room dashboard
        (paramedic + dispatcher view)
```

---

## System Architecture

### Component Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        ZERO-MINUTE DISPATCH                          │
│                                                                      │
│  ┌──────────────┐    HTTP/SSE     ┌────────────────────────────┐    │
│  │   Streamlit  │◄───────────────►│        FastAPI             │    │
│  │  Dashboard   │                 │   /analyze/stream (SSE)    │    │
│  │              │                 │   /analyze        (sync)   │    │
│  │  - Ops room  │                 └──────────┬─────────────────┘    │
│  │  - Live map  │                            │                      │
│  │  - SSE feed  │                            ▼                      │
│  └──────────────┘              ┌─────────────────────────┐          │
│                                │       pipeline.py        │          │
│                                │                          │          │
│                                │  analyze_emergency_      │          │
│                                │  scene_stream()          │          │
│                                │    │                     │          │
│                                │    ├─ upload to Gemini   │          │
│                                │    ├─ stream chunks      │          │
│                                │    └─ _post_process_     │          │
│                                │       triage()           │          │
│                                │         │                │          │
│                                │         ├─ BART NLP      │          │
│                                │         ├─ geocode       │          │
│                                │         ├─ hospital      │          │
│                                │         │  alert         │          │
│                                │         └─ TomTom ETA    │          │
│                                └─────────────────────────┘          │
│                                                                      │
│  External APIs:  Gemini 2.5 Flash · TomTom Routing · Nominatim OSM  │
│  Local models:   facebook/bart-large-mnli (zero-shot classification) │
└──────────────────────────────────────────────────────────────────────┘
```

### Request Lifecycle (Streaming Path)

```
Browser / Dashboard
    │
    │  POST /analyze/stream
    │  multipart: file + location (Form)
    │
    ▼
FastAPI  ──► write temp file ──► spawn analyze_emergency_scene_stream()
    │                                           │
    │                              ┌────────────▼───────────────┐
    │    SSE: "data: {chunk}\n\n"  │  1. genai.upload_file()    │
    │◄─────────────────────────────│  2. poll until ACTIVE      │
    │    (live as Gemini types)    │  3. stream=True generation │
    │                              │     yield each chunk.text  │
    │                              └────────────┬───────────────┘
    │                                           │ (full_text collected)
    │                              ┌────────────▼───────────────┐
    │                              │  _post_process_triage()    │
    │                              │  ├─ early scam exit (≥0.95)│
    │                              │  ├─ BART NLP scoring       │
    │                              │  ├─ ensemble decision      │
    │                              │  ├─ Nominatim geocoding    │
    │                              │  ├─ find_best_hospital()   │
    │                              │  ├─ TomTom route + ETA     │
    │                              │  ├─ Gemini hospital prep   │
    │                              │  └─ PriorityQueue assign   │
    │                              └────────────┬───────────────┘
    │    SSE: "data: [DONE]{...}\n\n"           │
    │◄──────────────────────────────────────────┘
    │    (full TriageReport JSON)
    │
    ▼
Dashboard parses [DONE] payload
    ├─ update session_state.last_report
    ├─ save to incident log
    ├─ decrement hospital resources
    ├─ TomTom route for ambulance map
    └─ st.rerun() → re-render ops room
```

---

## AI Pipeline Detail

### Stage 1 — Multimodal Scene Analysis (Gemini 2.5 Flash)

Gemini receives the raw file (video or audio) and the structured system prompt in a single API call. It processes both modalities simultaneously — visual frames for victim count, injury severity, and hazards; audio track for caller tone, location mentions, and distress level.

The model is constrained to output only a valid JSON object matching the triage schema. Temperature is fixed at 0.0 for deterministic, reproducible outputs.

```
System Prompt (defines exact JSON schema)
        +
Raw file (video or audio)
        ↓
Gemini 2.5 Flash
        ↓
Structured JSON:
  incident_metadata    → priority, confidence, victim count, location
  medical_entities     → condition, respiratory, consciousness
  environmental_hazards
  dispatch_recommendation
  scam_assessment      → gemini_scam_score (0.0 = genuine, 1.0 = scam)
```

**Streaming mode:** `stream=True` is passed to `generate_content()`. The server yields each text chunk to the dashboard via Server-Sent Events as it arrives, giving operators live visual feedback of the AI generating the triage report.

### Stage 2 — NLP Scam Cross-Check (facebook/bart-large-mnli)

After Gemini completes, the extracted `location_description` (which captures any spoken content from the caller) is passed through a separate zero-shot classification model loaded locally.

```
Transcript text
        ↓
bart-large-mnli (zero-shot)
        ↓
Candidate labels:
  "genuine emergency call"   →  score A
  "false alarm"              →  score B
  "prank call"               →  score C
        ↓
nlp_scam_score = B + C   (capped at 1.0)
```

The BART model is intentionally separate from Gemini. It provides an independent signal using a different architecture (discriminative NLI vs. generative LLM), making the ensemble more robust to adversarial inputs that might fool one model but not the other.

### Stage 3 — Ensemble Scam Decision

```
gemini_scam_score  +  nlp_scam_score
           ↓
   ┌───────────────────────────────────────┐
   │  gemini_scam_score ≥ 0.95?            │
   │  YES → IMMEDIATE SCAM EXIT            │
   │        skip all routing & hospital    │
   │        return CODE_GREEN + TRACE REQ  │
   └───────────────────────────────────────┘
           ↓ (NO)
   final_probability = (gemini + nlp) / 2
           ↓
   is_suspected_scam = True  if:
     final_probability > 0.6
     OR gemini_scam_score ≥ 0.75
```

**Why two thresholds?** The OR condition catches cases where Gemini is highly confident (e.g., caller is laughing — score 0.85) but the transcript is short, making the NLP score near 0 due to insufficient text. Without the OR, the average would stay below 0.6 and the scam would slip through.

### Stage 4 — Pydantic Validation

Every Gemini output passes through Pydantic v2 model validation before any downstream processing. This enforces:

- `confidence_score` strictly between 0.0 and 1.0
- `gemini_scam_score`, `nlp_scam_score`, `final_scam_probability` each between 0.0 and 1.0
- `priority_level` is one of `CODE_RED | CODE_ORANGE | CODE_GREEN` (enum)
- `requires_human_verification` is automatically set to `True` if `confidence_score < 0.85` or `final_scam_probability > 0.7`

Any malformed output from Gemini raises a `ValidationError` and is rejected before reaching the dashboard.

### Stage 5 — Hospital Routing

For genuine `CODE_RED` and `CODE_ORANGE` incidents, the pipeline:

1. **Specialty matching** — maps injury type (cardiac, neuro, burn, orthopedic, trauma) to the hospital with the matching specialty that has available bays
2. **Distance calculation** — Haversine formula from incident coordinates to each candidate hospital
3. **Real-time ETA** — TomTom Routing API with live traffic data; `travelTimeInSeconds` and `trafficDelayInSeconds` populate the hospital alert
4. **Preparation instructions** — a second Gemini call generates a 2-sentence briefing for the receiving ER staff based on condition, vitals, priority, and ETA

```
injury_type
    ↓
find_best_hospital()
    ├─ match specialty (cardiac / neuro / burns / ortho / trauma)
    ├─ filter available_bays > 0
    └─ sort by Haversine distance from incident lat/lon
           ↓
    best hospital selected
           ↓
get_traffic_route()  (TomTom API)
    ├─ real road travel time
    ├─ traffic delay in minutes
    └─ condition label (Clear / Moderate / Heavy)
           ↓
Gemini: generate preparation_instructions
           ↓
HospitalAlert populated
```

---

## Data Models

All inter-component data is typed and validated by Pydantic v2. The full schema:

```
TriageReport
├── IncidentMetadata
│   ├── priority_level: CODE_RED | CODE_ORANGE | CODE_GREEN
│   ├── confidence_score: float [0.0 – 1.0]
│   ├── estimated_victims: int
│   └── location_description: str | null
│
├── ExtractedMedicalEntities
│   ├── suspected_primary_condition: str
│   ├── respiratory_estimate: str   (e.g. "Rapid ~24 breaths/min")
│   └── consciousness_level: str
│
├── environmental_hazards: List[str]
│
├── DispatchRecommendation
│   ├── required_specialists: List[str]
│   ├── equipment_loadout: List[str]
│   ├── nearest_hospital: null   (populated by routing layer)
│   ├── nearest_fire_station: null
│   └── nearest_hydrant: null
│
├── ScamAssessment
│   ├── gemini_scam_score: float
│   ├── nlp_scam_score: float
│   ├── final_scam_probability: float
│   ├── is_suspected_scam: bool
│   └── scam_indicators: List[str]
│
├── HospitalAlert
│   ├── name: str
│   ├── city: str
│   ├── distance_km: float
│   ├── available_bays: int
│   ├── surgeons_on_call: List[str]
│   ├── equipment: List[str]
│   ├── eta_minutes: int
│   ├── preparation_instructions: str
│   └── traffic_route: TrafficRoute
│       ├── travel_time_minutes: int
│       ├── distance_km: float
│       ├── traffic_condition: str
│       └── traffic_delay_minutes: int
│
├── PriorityQueue
│   ├── queue_position: int
│   ├── total_active_incidents: int
│   ├── ambulances_available: int
│   └── priority_reason: str
│
└── requires_human_verification: bool
```

---

## Ambulance Dispatch Simulation

The operations dashboard maintains a live dispatch map powered by Folium on a CartoDB dark basemap. When a genuine incident is processed:

```
Incident confirmed (CODE_RED or CODE_ORANGE)
        ↓
dashboard_geocode(location_input)   ← Nominatim OSM
        ↓
get_tomtom_route_points(HQ → incident)   ← TomTom leg 1
get_tomtom_route_points(incident → hospital)   ← TomTom leg 2
        ↓
route_points = leg1 + leg2[1:]   ← single continuous road path
mid_idx = len(leg1) - 1          ← scene arrival index
        ↓
Ambulance entry stored in session_state:
  route_points: List[[lat, lon]]  (real road geometry)
  mid_idx: int                    (where ambulance reaches scene)
  step: int                       (current position index)
  total_steps: int
  status: EN_ROUTE → AT_SCENE → TO_HOSPITAL → ARRIVED
```

**SIMULATE DISPATCH** advances each active ambulance by 8% of its total route per click (`advance = max(1, int(total_steps * 0.08))`), status transitions driven by `mid_idx`.

Map markers use `components.html(m._repr_html_())` rather than `st_folium()` to avoid Streamlit's JSON serialization of Folium's Jinja2 template objects. This enables full use of `folium.DivIcon`, `folium.Element`, and styled tooltips.

---

## Operations Dashboard

The dashboard is a single-page Streamlit application with a three-column layout:

```
┌─────────────────────────────────────────────────────────────────┐
│  NAVBAR: brand · active/today/scam counters · LIVE indicator    │
│  TICKER: scrolling real-time incident feed                      │
├─────────────────┬───────────────────────────┬───────────────────┤
│  LEFT COLUMN    │     MIDDLE COLUMN         │  RIGHT COLUMN     │
│                 │                           │                   │
│  Incident Log   │  Scene Recording upload   │  Hospital         │
│  (real-time)    │  Location input           │  Resources        │
│                 │  ANALYZE button           │                   │
│  - Priority     │                           │  - Charles Nicolle│
│    badge        │  ── DISPATCH MAP ──       │  - Habib Thameur  │
│  - Condition    │  Dark Folium map          │  - Militaire      │
│  - Location     │  HQ ★ marker              │  - Les Oliviers   │
│  - Time         │  Hospital ✚ markers       │                   │
│  - Hospital     │  Incident ● circles       │  Each card shows: │
│                 │  Ambulance cards + routes │  - bays / surgeons│
│                 │  In-map legend            │  - ambulances     │
│                 │  SIMULATE DISPATCH btn    │  - status         │
│                 │                           │                   │
│                 │  ── TRIAGE REPORT ──      │                   │
│                 │  Priority banner          │                   │
│                 │  Medical entities         │                   │
│                 │  Scam assessment          │                   │
│                 │  Hospital alert           │                   │
│                 │  Dispatch recommendation  │                   │
│                 │  Human verification flag  │                   │
└─────────────────┴───────────────────────────┴───────────────────┘
```

When the Analyze button is pressed, the dashboard opens a streaming SSE connection to `/analyze/stream`. A live monospace terminal in the middle column displays raw Gemini JSON as it generates. When `[DONE]` arrives, the terminal clears and the full structured report renders.

---

## API Reference

### `POST /analyze/stream`

Streaming endpoint. Returns Server-Sent Events.

| Field | Type | Description |
|---|---|---|
| `file` | multipart file | Video (mp4, webm, mpeg4) or audio (mp3, wav, m4a, ogg) |
| `location` | Form string (optional) | Incident location text for geocoding |

**Response stream:**
```
data: {"incident_metadata": ...   ← raw Gemini text chunk (partial JSON)
data: "priority_level": "CODE_   ← next chunk
...
data: [DONE]{"incident_metadata": {...}, "hospital_alert": {...}, ...}
```

The `[DONE]` prefix signals the final, fully post-processed `TriageReport` JSON. All preceding `data:` lines are raw Gemini generation chunks for live display only.

### `POST /analyze`

Synchronous endpoint. Returns the same `TriageReport` JSON in a single response after the full pipeline completes.

### `GET /health`

```json
{"status": "operational", "system": "Zero-Minute Dispatch"}
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Multimodal AI | Gemini 2.5 Flash | Video + audio analysis in one API call, streaming generation |
| NLP Scam Detection | facebook/bart-large-mnli | Zero-shot classification, independent of Gemini |
| Backend | FastAPI + Pydantic v2 | Async SSE streaming, schema enforcement |
| Frontend | Streamlit | Operations room dashboard |
| Map | Folium + CartoDB dark | Ambulance dispatch visualization on real basemap |
| Routing | TomTom Routing API | Real-time road ETA with traffic data |
| Geocoding | Nominatim (OpenStreetMap) | Location text → coordinates |
| CI/CD | GitHub Actions | Test on push to main/dev, PR auto-creation dev → main |

---

## Project Structure

```
Zero-Minute-Dispatch/
│
├── app/
│   ├── main.py              FastAPI application
│   │                        /analyze/stream  — SSE streaming endpoint
│   │                        /analyze         — synchronous endpoint
│   │                        /health          — liveness check
│   │
│   ├── pipeline.py          Core AI pipeline
│   │                        analyze_emergency_scene_stream() — yields SSE chunks then final dict
│   │                        analyze_emergency_scene()        — synchronous wrapper
│   │                        _post_process_triage()           — shared post-processing (NLP, routing)
│   │                        generate_hospital_alert()        — TomTom + Gemini hospital prep
│   │                        detect_scam_nlp()                — BART zero-shot classification
│   │                        geocode_location()               — Nominatim geocoding
│   │
│   ├── models.py            Pydantic v2 schema
│   │                        TriageReport, IncidentMetadata, ExtractedMedicalEntities
│   │                        ScamAssessment, HospitalAlert, TrafficRoute, PriorityQueue
│   │
│   └── hospital.py          Hospital registry for Tunisia
│                            find_best_hospital() — specialty match + Haversine distance sort
│
├── frontend/
│   └── dashboard.py         Streamlit operations dashboard
│                            Three-column ops room layout
│                            SSE streaming consumer with live terminal
│                            Folium dark map with real TomTom road geometry
│                            Ambulance dispatch simulation (8% per step)
│
├── tests/
│   └── test_schema.py       Pydantic validation tests
│                            valid report, invalid confidence score, verification flag
│
├── .github/
│   └── workflows/
│       ├── ci.yml           Run pytest on push to main/dev
│       └── cd.yml           Auto PR: dev → main
│
├── .env.example             GOOGLE_API_KEY, TOMTOM_API_KEY
├── requirements.txt
└── README.md
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- [Google AI Studio API key](https://aistudio.google.com) (free)
- [TomTom Developer API key](https://developer.tomtom.com) (free tier)

### Installation

```bash
git clone https://github.com/PublisherX02/Zero-Minute-Dispatch.git
cd Zero-Minute-Dispatch

python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Linux / Mac

pip install -r requirements.txt

# Pre-download the BART model (avoids cold-start delay on first analysis)
python download_models.py

cp .env.example .env
# Edit .env — add GOOGLE_API_KEY and TOMTOM_API_KEY
```

### Running

```bash
# Terminal 1 — API server
uvicorn app.main:app --reload

# Terminal 2 — Dashboard
streamlit run frontend/dashboard.py
```

Open `http://localhost:8501`.

### Testing

```bash
pytest tests/ -v
```

---

## Roadmap

### Phase 1 — MVP (Current)

- Multimodal video and audio scene analysis via Gemini 2.5 Flash
- Streaming SSE pipeline with live terminal output in the ops room
- Ensemble scam detection: Gemini + BART-large-mnli
- Pydantic v2 schema enforcement with human verification flagging
- Hospital specialty matching with real-time TomTom traffic ETA
- Gemini-generated ER preparation instructions
- Folium operations map: real TomTom road geometry for ambulance routes
- Ambulance dispatch simulation with 8%-per-step progress tracking
- Civil Protection ops room dashboard: dark theme, live incident log, hospital resource tracker

### Phase 2 — Scale (Pending Governmental Authorization)

- Municipal CCTV network integration for passive incident detection
- Automatic triage without caller reporting (camera-triggered)
- YOLOv8 victim counting from fixed camera feeds
- GPS location capture via SMS link to caller

### Phase 3 — Intelligence

- XGBoost / LSTM predictive heatmaps for pre-positioning
- Tunisian Derja dialect NLP integration
- CAD system integration via standard JSON schema
- Multi-incident priority arbitration

---

## Field Validation

Validated through direct interviews with:

- **Civil Protection Officials** — confirmed the Blind Arrival operational gap; explicitly requested the scam detection module and the ops room dashboard
- **Emergency Medical Doctors** — validated the medical consequences of incomplete pre-arrival information; confirmed the triage schema fields match actual dispatch needs

Key findings:
- Dispatchers currently relay verbal descriptions only — no structured data reaches paramedics
- False emergency calls represent a significant resource drain (~15% dispatch rate estimate)
- Most critical pre-arrival data: victim count, primary condition, and precise location

---

## Disclaimer

Zero-Minute Dispatch is a research prototype built for educational and hackathon purposes. It is not certified for clinical or operational deployment. All AI outputs require human verification before any emergency action is taken.

---

## Built By

**Mohamed Mouelhi**  
First-Year Computer Engineering Student  
NVIDIA Certified — Generative AI / LLM & Deep Learning  
Microsoft Summer Intern 2026

*Humanovators 2.0 — April 2026*
