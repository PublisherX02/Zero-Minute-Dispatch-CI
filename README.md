# Zero-Minute Dispatch
[![Zero-Minute Dispatch CI](https://github.com/PublisherX02/Zero-Minute-Dispatch-CI/actions/workflows/ci.yml/badge.svg)](https://github.com/PublisherX02/Zero-Minute-Dispatch-CI/actions/workflows/ci.yml)
[![Auto Pull Request to Main](https://github.com/PublisherX02/Zero-Minute-Dispatch-CI/actions/workflows/cd.yml/badge.svg)](https://github.com/PublisherX02/Zero-Minute-Dispatch-CI/actions/workflows/cd.yml)

# Zero-Minute Dispatch
[![Zero-Minute Dispatch CI](https://github.com/PublisherX02/Zero-Minute-Dispatch-CI/actions/workflows/ci.yml/badge.svg)](https://github.com/PublisherX02/Zero-Minute-Dispatch-CI/actions/workflows/ci.yml)
[![Auto Pull Request to Main](https://github.com/PublisherX02/Zero-Minute-Dispatch-CI/actions/workflows/cd.yml/badge.svg)](https://github.com/PublisherX02/Zero-Minute-Dispatch-CI/actions/workflows/cd.yml)

> **Eliminating the "Blind Arrival" in Emergency Medical Response**

Built for **Humanovators 2.0 Hackathon** — Theme: Smart Mobility for Healthcare  
Challenge Area: Dynamic Vehicle Routing for Emergency Medical Services (EMS)

> 🏆 **1st Place Winner — Humanovators 2.0 Hackathon, April 2026**  
> Ranked 1st across all three judging dimensions against 13+ competing teams.

> Validated through direct field interviews with Civil Protection Officials — Tunisia, April 2026

---

## Recognition

**Zero-Minute Dispatch won first place at Humanovators 2.0** (April 2026), Tunisia's Smart Mobility for Healthcare hackathon, competing against 13+ teams across all challenge areas.

The project ranked first in every judging dimension:
- **Technical Implementation** — multimodal AI pipeline, real-time streaming, containerized deployment
- **Field Validation** — direct Civil Protection engagement, feature requests from active-duty officers
- **Impact & Scalability** — concrete national deployment pathway with government partnership

Civil Protection officers who validated the project during field research have expressed interest in continued collaboration toward a national pilot deployment.

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

Field interviews with Civil Protection officers identified four specific gaps:

| Gap | Current Reality | Impact |
|---|---|---|
| Victim count | Dispatcher estimate only | Wrong resources dispatched |
| Injury type | Verbal description | Wrong equipment loaded |
| False calls | No validation protocol | ~15% of dispatches wasted |
| Hospital readiness | No pre-alert sent | ER unprepared on arrival |

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

### Stage 4 — Pydantic Validation

Every Gemini output passes through Pydantic v2 model validation before any downstream processing. This enforces:

- `confidence_score` strictly between 0.0 and 1.0
- `gemini_scam_score`, `nlp_scam_score`, `final_scam_probability` each between 0.0 and 1.0
- `priority_level` is one of `CODE_RED | CODE_ORANGE | CODE_GREEN` (enum)
- `requires_human_verification` is automatically set to `True` if `confidence_score < 0.85` or `final_scam_probability > 0.7`

### Stage 5 — Hospital Routing

For genuine `CODE_RED` and `CODE_ORANGE` incidents, the pipeline:

1. **Specialty matching** — maps injury type (cardiac, neuro, burn, orthopedic, trauma) to the hospital with the matching specialty that has available bays
2. **Distance calculation** — Haversine formula from incident coordinates to each candidate hospital
3. **Real-time ETA** — TomTom Routing API with live traffic data
4. **Preparation instructions** — a second Gemini call generates a 2-sentence briefing for the receiving ER staff

---

## Data Models

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
│   ├── respiratory_estimate: str
│   └── consciousness_level: str
│
├── environmental_hazards: List[str]
│
├── DispatchRecommendation
│   ├── required_specialists: List[str]
│   └── equipment_loadout: List[str]
│
├── ScamAssessment
│   ├── gemini_scam_score: float
│   ├── nlp_scam_score: float
│   ├── final_scam_probability: float
│   ├── is_suspected_scam: bool
│   └── scam_indicators: List[str]
│
├── HospitalAlert
│   ├── name, city, distance_km, available_bays
│   ├── surgeons_on_call: List[str]
│   ├── equipment: List[str]
│   ├── eta_minutes: int
│   ├── preparation_instructions: str
│   └── traffic_route: TrafficRoute
│
├── PriorityQueue
│   ├── queue_position: int
│   ├── ambulances_available: int
│   └── priority_reason: str
│
└── requires_human_verification: bool
```

---

## Operations Dashboard

Three-column Streamlit ops room:

```
┌─────────────────────────────────────────────────────────────────┐
│  NAVBAR: brand · active/today/scam counters · LIVE indicator    │
│  TICKER: scrolling real-time incident feed                      │
├─────────────────┬───────────────────────────┬───────────────────┤
│  Incident Log   │  Upload + Analyze         │  Hospital         │
│  (real-time)    │  Dispatch Map (Folium)    │  Resources        │
│                 │  Triage Report            │  (live depletion) │
└─────────────────┴───────────────────────────┴───────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Multimodal AI | Gemini 2.5 Flash |
| NLP Scam Detection | facebook/bart-large-mnli |
| Backend | FastAPI + Pydantic v2 |
| Frontend | Streamlit |
| Map | Folium + CartoDB dark |
| Routing | TomTom Routing API |
| Geocoding | Nominatim (OpenStreetMap) |
| CI/CD | GitHub Actions |
| Containers | Docker + docker-compose |

---

## Quick Start

```bash
git clone https://github.com/PublisherX02/Zero-Minute-Dispatch-CI.git
cd Zero-Minute-Dispatch-CI

python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Linux / Mac

pip install -r requirements.txt
python download_models.py

cp .env.example .env
# Add GOOGLE_API_KEY and TOMTOM_API_KEY
```

```bash
# Terminal 1
uvicorn app.main:app --reload

# Terminal 2
streamlit run frontend/dashboard.py
```

```bash
pytest tests/ -v
```

---

## Roadmap

### Phase 1 — MVP ✅ Complete

- Multimodal video and audio scene analysis
- Streaming SSE pipeline with live terminal output
- Ensemble scam detection: Gemini + BART-large-mnli
- Hospital specialty matching with TomTom real-time ETA
- Gemini-generated ER preparation instructions
- Live operations dashboard with ambulance dispatch simulation
- CI/CD pipeline + Docker containerization

### Phase 2 — National Deployment

- Mobile application for Civil Protection dispatchers
- National distribution through Civil Protection channels and radio stations
- GPS location capture via SMS link to caller
- Tunisian Derja dialect NLP integration
- CAD system integration via standard JSON schema

### Phase 3 — Autonomous Detection *(pending governmental authorization)*

- Municipal CCTV network integration for passive incident detection
- Automatic triage without caller reporting — camera-triggered on accident detection only
- YOLOv8 victim counting from fixed camera feeds
- No mass surveillance — AI triggers exclusively on accident or human risk detection
- No continuous recording, no facial recognition, no behavioral tracking

### Phase 4 — Predictive Intelligence

- XGBoost / LSTM predictive heatmaps trained on historical accident data, weather, traffic, and tourist influx
- Pre-positioning of ambulances in high-risk zones before emergencies occur
- Multi-incident priority arbitration across regional networks

---

## Field Validation

Validated through direct field interviews with **Civil Protection Officials** at the Civil Protection Operations Center, Tunisia — April 2026.

Key findings from field research:
- Dispatchers currently relay verbal descriptions only — no structured data reaches paramedics
- Officers confirmed three operational failures: no digitalization, no location tracking, no structured multi-victim assessment
- Active-duty officers explicitly requested the scam detection module and the operations room dashboard
- Civil Protection offered national distribution channels for Phase 2 deployment

> *"An operations room dashboard showing real-time structured intelligence the moment a call comes in."*  
> — Civil Protection Officer, Tunisia 2026

---

## Hospital Network (Tunisia)

| Hospital | City | Specialties |
|---|---|---|
| Hôpital Charles Nicolle | Tunis | Trauma, Cardiac, Neurology, Burns |
| Hôpital Habib Thameur | Tunis | Trauma, Orthopedic, General |
| Hôpital Militaire de Tunis | Tunis | Trauma, Cardiac, Neurology |
| Clinique Les Oliviers | Tunis | Cardiac, General |
| Hôpital Régional de Bizerte | Bizerte | Trauma, General |
| Hôpital Farhat Hached | Sousse | Trauma, Cardiac, Neurology |
| Hôpital Hédi Chaker | Sfax | Trauma, Burns, Orthopedic |
| Hôpital Mohamed Tahar Maamouri | Nabeul | Trauma, General |
| Hôpital Régional de Béja | Béja | General, Trauma |

---

## Disclaimer

Zero-Minute Dispatch is a research prototype. It is not certified for clinical or operational deployment. All AI outputs require human verification by trained dispatchers before any emergency action is taken.

---

## Built By

**Mohamed Mouelhi**  
First-Year Computer Engineering Student  
NVIDIA Certified — Generative AI / LLM & Deep Learning  
Microsoft Summer Intern 2026

🏆 *1st Place — Humanovators 2.0 Hackathon, April 2026*

