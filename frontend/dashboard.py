import streamlit as st
import requests
from datetime import datetime

st.set_page_config(
    page_title="ZERO-MINUTE DISPATCH | Command Center",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── SESSION STATE ─────────────────────────────────────────────────────────────
if "active_incidents" not in st.session_state:
    st.session_state.active_incidents = 0
if "last_incident_time" not in st.session_state:
    st.session_state.last_incident_time = "—"

# ── MASTER CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>

/* ── GLOBAL ── */
html, body, [class*="css"] {
    background-color: #0a0a0a !important;
    color: #b8b8b8 !important;
    font-family: 'Courier New', 'Lucida Console', monospace !important;
}
.stApp { background-color: #0a0a0a !important; }
.block-container { padding: 1rem 2rem 2rem 2rem !important; max-width: 100% !important; }
* { box-sizing: border-box; }

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background-color: #070707 !important;
    border-right: 1px solid #2a0000 !important;
    min-width: 220px !important;
}
[data-testid="stSidebarContent"] { padding: 1rem 0.8rem !important; }
section[data-testid="stSidebar"] > div { background-color: #070707 !important; }

/* ── HEADER ── */
.ops-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    border-bottom: 2px solid #8B0000;
    padding-bottom: 0.9rem;
    margin-bottom: 1.4rem;
}
.ops-title {
    font-size: 1.5em;
    font-weight: 900;
    color: #ffffff;
    letter-spacing: 0.25em;
    text-transform: uppercase;
}
.ops-subtitle {
    font-size: 0.68em;
    color: #555;
    letter-spacing: 0.18em;
    margin-top: 0.2rem;
}
.ops-timestamp {
    font-size: 0.7em;
    color: #8B0000;
    text-align: right;
    letter-spacing: 0.08em;
    line-height: 1.6;
}

/* ── SIDEBAR ELEMENTS ── */
.sb-section {
    font-size: 0.6em;
    letter-spacing: 0.25em;
    color: #8B0000;
    text-transform: uppercase;
    padding-bottom: 0.35rem;
    border-bottom: 1px solid #2a0000;
    margin: 1rem 0 0.6rem 0;
}
.sb-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.28rem 0;
    border-bottom: 1px solid #111;
}
.sb-label { font-size: 0.65em; color: #555; letter-spacing: 0.08em; text-transform: uppercase; }
.sb-online  { font-size: 0.65em; color: #33cc33; font-weight: 700; letter-spacing: 0.05em; }
.sb-standby { font-size: 0.65em; color: #cc9900; font-weight: 700; letter-spacing: 0.05em; }
.sb-offline { font-size: 0.65em; color: #cc3333; font-weight: 700; letter-spacing: 0.05em; }
.sb-count   { font-size: 1.1em;  color: #ffffff; font-weight: 900; }

/* ── UPLOAD ZONE ── */
.upload-zone {
    background-color: #0d0d0d;
    border: 1px solid #2a0000;
    padding: 1.1rem 1.3rem 0.5rem 1.3rem;
    margin-bottom: 1.2rem;
}
.zone-title {
    font-size: 0.62em;
    letter-spacing: 0.22em;
    color: #8B0000;
    text-transform: uppercase;
    margin-bottom: 0.7rem;
    border-bottom: 1px solid #2a0000;
    padding-bottom: 0.3rem;
}

/* ── PANELS ── */
.panel {
    background-color: #0e0e0e;
    border: 1px solid #1c1c1c;
    border-left: 3px solid #8B0000;
    padding: 1rem 1.2rem;
    margin-bottom: 0.9rem;
}
.panel-critical {
    background-color: #0f0000;
    border: 1px solid #3a0000;
    border-left: 3px solid #cc2200;
    padding: 1rem 1.2rem;
    margin-bottom: 0.9rem;
}
.panel-warning {
    background-color: #0d0700;
    border: 1px solid #382000;
    border-left: 3px solid #cc6600;
    padding: 1rem 1.2rem;
    margin-bottom: 0.9rem;
}
.panel-safe {
    background-color: #000e00;
    border: 1px solid #003800;
    border-left: 3px solid #006600;
    padding: 1rem 1.2rem;
    margin-bottom: 0.9rem;
}
.panel-title {
    font-size: 0.62em;
    letter-spacing: 0.22em;
    color: #8B0000;
    text-transform: uppercase;
    margin-bottom: 0.7rem;
    border-bottom: 1px solid #1e0000;
    padding-bottom: 0.3rem;
}

/* ── PULSING BANNERS ── */
@keyframes pulse-red {
    0%   { box-shadow: 0 0 8px #8B0000; border-color: #8B0000; }
    50%  { box-shadow: 0 0 28px #cc0000, 0 0 50px #8B0000; border-color: #ff2222; }
    100% { box-shadow: 0 0 8px #8B0000; border-color: #8B0000; }
}
@keyframes pulse-orange {
    0%   { box-shadow: 0 0 8px #7a3800; border-color: #cc6600; }
    50%  { box-shadow: 0 0 28px #ff8800, 0 0 50px #7a3800; border-color: #ffaa44; }
    100% { box-shadow: 0 0 8px #7a3800; border-color: #cc6600; }
}
@keyframes pulse-green {
    0%   { box-shadow: 0 0 8px #004d00; border-color: #006600; }
    50%  { box-shadow: 0 0 28px #009900, 0 0 50px #004d00; border-color: #00bb00; }
    100% { box-shadow: 0 0 8px #004d00; border-color: #006600; }
}
@keyframes pulse-yellow {
    0%   { box-shadow: 0 0 8px #665000; border-color: #aa8800; }
    50%  { box-shadow: 0 0 28px #ddbb00, 0 0 50px #665000; border-color: #ffdd00; }
    100% { box-shadow: 0 0 8px #665000; border-color: #aa8800; }
}

.banner-red {
    background-color: #130000;
    border: 2px solid #8B0000;
    color: #ff2222;
    padding: 1.1rem 2rem;
    text-align: center;
    font-size: 1.7em;
    font-weight: 900;
    letter-spacing: 0.35em;
    text-transform: uppercase;
    margin-bottom: 1rem;
    animation: pulse-red 1.8s ease-in-out infinite;
}
.banner-orange {
    background-color: #130800;
    border: 2px solid #cc6600;
    color: #ff8833;
    padding: 1.1rem 2rem;
    text-align: center;
    font-size: 1.7em;
    font-weight: 900;
    letter-spacing: 0.35em;
    text-transform: uppercase;
    margin-bottom: 1rem;
    animation: pulse-orange 1.8s ease-in-out infinite;
}
.banner-green {
    background-color: #001300;
    border: 2px solid #006600;
    color: #33cc33;
    padding: 1.1rem 2rem;
    text-align: center;
    font-size: 1.7em;
    font-weight: 900;
    letter-spacing: 0.35em;
    text-transform: uppercase;
    margin-bottom: 1rem;
    animation: pulse-green 2s ease-in-out infinite;
}
.banner-scam {
    background-color: #131000;
    border: 2px solid #aa8800;
    color: #ffdd00;
    padding: 1.1rem 2rem;
    text-align: center;
    font-size: 1.7em;
    font-weight: 900;
    letter-spacing: 0.3em;
    text-transform: uppercase;
    margin-bottom: 1rem;
    animation: pulse-yellow 1.4s ease-in-out infinite;
}
.banner-verify {
    background-color: #130000;
    border: 2px solid #cc0000;
    color: #ff4444;
    padding: 0.7rem 2rem;
    text-align: center;
    font-size: 1em;
    font-weight: 900;
    letter-spacing: 0.25em;
    text-transform: uppercase;
    margin-bottom: 0.9rem;
    animation: pulse-red 1.2s ease-in-out infinite;
}

/* ── METRICS GRID ── */
.metrics-grid {
    display: grid;
    gap: 0.7rem;
    margin-top: 0.4rem;
}
.cols-3 { grid-template-columns: repeat(3, 1fr); }
.cols-2 { grid-template-columns: repeat(2, 1fr); }
.cols-4 { grid-template-columns: repeat(4, 1fr); }

.metric-card {
    background-color: #111;
    border: 1px solid #1e1e1e;
    padding: 0.8rem 1rem;
    text-align: center;
}
.metric-label {
    font-size: 0.6em;
    letter-spacing: 0.18em;
    color: #555;
    text-transform: uppercase;
    margin-bottom: 0.35rem;
}
.metric-value       { font-size: 1.5em; font-weight: 900; color: #ffffff; }
.metric-value-red   { font-size: 1.5em; font-weight: 900; color: #ff3333; }
.metric-value-orange{ font-size: 1.5em; font-weight: 900; color: #ff8833; }
.metric-value-green { font-size: 1.5em; font-weight: 900; color: #33cc33; }
.metric-value-yellow{ font-size: 1.5em; font-weight: 900; color: #ffdd00; }

/* ── DATA TABLE ── */
.data-table { margin-top: 0.3rem; }
.data-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.28rem 0;
    border-bottom: 1px solid #161616;
}
.data-label  { font-size: 0.65em; color: #4a4a4a; letter-spacing: 0.1em; text-transform: uppercase; }
.dv          { font-size: 0.82em; font-weight: 700; color: #cccccc; }
.dv-red      { font-size: 0.82em; font-weight: 700; color: #ff4444; }
.dv-orange   { font-size: 0.82em; font-weight: 700; color: #ff8833; }
.dv-green    { font-size: 0.82em; font-weight: 700; color: #44cc44; }

/* ── LISTS ── */
.list-item {
    padding: 0.27rem 0;
    border-bottom: 1px solid #181818;
    font-size: 0.8em;
    color: #c0c0c0;
}
.list-item-red {
    padding: 0.27rem 0;
    border-bottom: 1px solid #2a0000;
    font-size: 0.8em;
    color: #ff8888;
}
.list-item-orange {
    padding: 0.27rem 0;
    border-bottom: 1px solid #2a1400;
    font-size: 0.8em;
    color: #ffaa66;
}

/* ── TWO-COLUMN CONTENT ── */
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 1.2rem; margin-top: 0.4rem; }
.sub-label {
    font-size: 0.62em;
    letter-spacing: 0.18em;
    color: #555;
    text-transform: uppercase;
    margin-bottom: 0.4rem;
    padding-bottom: 0.2rem;
    border-bottom: 1px solid #1c1c1c;
}

/* ── PREPARATION BOX ── */
.prep-box {
    margin-top: 0.8rem;
    padding: 0.65rem 0.9rem;
    background: #0b0600;
    border-left: 2px solid #cc6600;
}
.prep-label {
    font-size: 0.6em;
    letter-spacing: 0.18em;
    color: #cc6600;
    text-transform: uppercase;
    margin-bottom: 0.3rem;
}
.prep-text { font-size: 0.82em; color: #ffaa66; }

/* ── SCAM PROB BAR ── */
.prob-bar-track {
    background-color: #1a1a1a;
    height: 6px;
    margin-top: 0.3rem;
    margin-bottom: 0.5rem;
    width: 100%;
}
.prob-bar-fill {
    height: 6px;
    background-color: #ffdd00;
}

/* ── INPUTS ── */
.stTextInput > div > div > input {
    background-color: #0d0d0d !important;
    border: 1px solid #2a0000 !important;
    color: #cccccc !important;
    font-family: 'Courier New', monospace !important;
    border-radius: 0 !important;
    font-size: 0.9em !important;
}
.stTextInput > div > div > input:focus {
    border-color: #8B0000 !important;
    box-shadow: 0 0 6px #8B000066 !important;
}
label[data-testid="stWidgetLabel"] {
    color: #555 !important;
    font-size: 0.7em !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    font-family: 'Courier New', monospace !important;
}

/* ── FILE UPLOADER ── */
[data-testid="stFileUploaderDropzone"] {
    background-color: #0d0d0d !important;
    border: 1px dashed #2a0000 !important;
    border-radius: 0 !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] {
    color: #444 !important;
    font-family: 'Courier New', monospace !important;
    font-size: 0.85em !important;
}

/* ── BUTTON ── */
.stButton > button {
    background-color: #8B0000 !important;
    color: #ffffff !important;
    border: 1px solid #cc0000 !important;
    font-family: 'Courier New', monospace !important;
    font-size: 1.05em !important;
    font-weight: 900 !important;
    letter-spacing: 0.22em !important;
    text-transform: uppercase !important;
    border-radius: 0 !important;
    padding: 0.65rem 2rem !important;
    transition: all 0.15s ease !important;
    width: 100% !important;
}
.stButton > button:hover {
    background-color: #aa0000 !important;
    box-shadow: 0 0 18px #8B000088 !important;
}
.stButton > button:disabled {
    background-color: #1e0000 !important;
    color: #444 !important;
    border-color: #2a0000 !important;
}

/* ── EXPANDER ── */
[data-testid="stExpander"] {
    background-color: #0d0d0d !important;
    border: 1px solid #1c1c1c !important;
    border-radius: 0 !important;
}
[data-testid="stExpander"] summary {
    color: #555 !important;
    font-size: 0.75em !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
    font-family: 'Courier New', monospace !important;
}

/* ── SPINNER ── */
[data-testid="stSpinner"] > div {
    border-top-color: #8B0000 !important;
}

/* ── SCROLLBAR ── */
::-webkit-scrollbar       { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #0a0a0a; }
::-webkit-scrollbar-thumb { background: #8B0000; }

/* ── DIVIDER ── */
hr { border-color: #1e0000 !important; margin: 0.7rem 0 !important; }

/* ── JSON ── */
.stJson { background-color: #0d0d0d !important; }
pre { background-color: #0a0a0a !important; color: #888 !important; font-size: 0.78em !important; }

</style>
""", unsafe_allow_html=True)


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
def check_api_health() -> bool:
    try:
        r = requests.get("http://localhost:8000/", timeout=2)
        return r.status_code < 500
    except Exception:
        return False


with st.sidebar:
    now_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H:%M:%S")

    st.markdown(f"""
    <div style="text-align:center; padding:0.5rem 0 0.8rem 0; border-bottom:1px solid #2a0000;">
        <div style="font-size:0.6em; letter-spacing:0.3em; color:#8B0000; text-transform:uppercase;">
            &#9632; COMMAND CENTER &#9632;
        </div>
        <div style="font-size:0.55em; color:#333; margin-top:0.2rem; letter-spacing:0.1em;">
            CIVIL PROTECTION OPS
        </div>
    </div>
    """, unsafe_allow_html=True)

    api_online = check_api_health()
    api_dot   = "&#9679;" if api_online else "&#9679;"
    api_class = "sb-online" if api_online else "sb-standby"
    api_text  = "ONLINE" if api_online else "STANDBY"

    st.markdown(f"""
    <div class="sb-section">&#9632; System Status</div>
    <div class="sb-row">
        <span class="sb-label">SYSTEM</span>
        <span class="sb-online">&#9679; OPERATIONAL</span>
    </div>
    <div class="sb-row">
        <span class="sb-label">AI PIPELINE</span>
        <span class="sb-online">&#9679; READY</span>
    </div>
    <div class="sb-row">
        <span class="sb-label">DISPATCH NET</span>
        <span class="sb-online">&#9679; ACTIVE</span>
    </div>
    <div class="sb-row">
        <span class="sb-label">HOSPITAL LINK</span>
        <span class="sb-online">&#9679; CONNECTED</span>
    </div>

    <div class="sb-section">&#9632; API Status</div>
    <div class="sb-row">
        <span class="sb-label">ENDPOINT</span>
        <span class="{api_class}">&#9679; {api_text}</span>
    </div>
    <div class="sb-row">
        <span class="sb-label">HOST</span>
        <span class="sb-standby">localhost:8000</span>
    </div>
    <div class="sb-row">
        <span class="sb-label">TIMEOUT</span>
        <span class="sb-standby">120s</span>
    </div>

    <div class="sb-section">&#9632; Incident Log</div>
    <div class="sb-row">
        <span class="sb-label">ACTIVE INCIDENTS</span>
        <span class="sb-count">{st.session_state.active_incidents}</span>
    </div>
    <div class="sb-row">
        <span class="sb-label">SESSION DATE</span>
        <span class="sb-standby">{now_str}</span>
    </div>
    <div class="sb-row">
        <span class="sb-label">LAST ANALYSIS</span>
        <span class="sb-standby">{st.session_state.last_incident_time}</span>
    </div>

    <div class="sb-section">&#9632; Classification</div>
    <div class="sb-row">
        <span class="sb-label" style="color:#ff3333;">CODE RED</span>
        <span class="sb-offline">CRITICAL</span>
    </div>
    <div class="sb-row">
        <span class="sb-label" style="color:#ff8833;">CODE ORANGE</span>
        <span class="sb-standby">URGENT</span>
    </div>
    <div class="sb-row">
        <span class="sb-label" style="color:#44cc44;">CODE GREEN</span>
        <span class="sb-online">NON-CRITICAL</span>
    </div>
    <div class="sb-row">
        <span class="sb-label" style="color:#ffdd00;">SCAM ALERT</span>
        <span style="font-size:0.65em; color:#ffdd00; font-weight:700;">NO DISPATCH</span>
    </div>

    <div style="margin-top:1.2rem; padding-top:0.8rem; border-top:1px solid #1a0000;
                font-size:0.55em; color:#2a2a2a; letter-spacing:0.1em; text-align:center;">
        ZERO-MINUTE DISPATCH v2.0<br>
        AI TRIAGE SYSTEM — {now_str}
    </div>
    """, unsafe_allow_html=True)


# ── MAIN HEADER ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="ops-header">
    <div>
        <div class="ops-title">&#9632; ZERO-MINUTE DISPATCH</div>
        <div class="ops-subtitle">
            CIVIL PROTECTION COMMAND CENTER &nbsp;|&nbsp;
            AI EMERGENCY TRIAGE SYSTEM &nbsp;|&nbsp;
            REAL-TIME DISPATCH OPERATIONS
        </div>
    </div>
    <div class="ops-timestamp">
        OPERATOR TERMINAL<br>
        {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} UTC<br>
        <span style="color:#333;">SESSION ACTIVE</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ── INPUT ZONE ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="upload-zone">
    <div class="zone-title">&#9632; Incident Input — Upload Emergency Scene Recording</div>
</div>
""", unsafe_allow_html=True)

col_file, col_loc = st.columns([3, 2])
with col_file:
    uploaded_file = st.file_uploader(
        "Scene Recording (Video / Audio)",
        type=["mp4", "mp3", "wav", "m4a", "ogg", "webm"],
        help="Upload video or audio from the emergency scene.",
        label_visibility="visible"
    )
with col_loc:
    location_input = st.text_input(
        "Incident Location",
        placeholder="e.g. Route Nationale 9, Sidi Bou Said",
        help="GPS coordinates or street address"
    )

st.button(
    "&#9632;  ANALYZE EMERGENCY SCENE  &#9632;",
    type="primary",
    use_container_width=True,
    key="analyze_btn",
    disabled=not bool(uploaded_file)
)
analyze_clicked = st.session_state.get("analyze_btn", False)


# ── ANALYSIS & RESULTS ────────────────────────────────────────────────────────
if uploaded_file and analyze_clicked:

    with st.spinner("AI pipeline processing — analyzing scene..."):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        form_data = {"location": location_input} if location_input else {}
        try:
            response = requests.post(
                "http://localhost:8000/analyze",
                files=files,
                data=form_data or None,
                timeout=120
            )
            response.raise_for_status()
            data = response.json()
        except requests.Timeout:
            st.markdown("""
            <div class="banner-red">
                &#9888; PIPELINE TIMEOUT — ANALYSIS EXCEEDED 120 SECONDS
            </div>
            """, unsafe_allow_html=True)
            st.stop()
        except requests.ConnectionError:
            st.markdown("""
            <div class="banner-red">
                &#9888; CONNECTION REFUSED — VERIFY API ENDPOINT: localhost:8000
            </div>
            """, unsafe_allow_html=True)
            st.stop()
        except Exception as e:
            st.markdown(f"""
            <div class="banner-red">
                &#9888; PIPELINE ERROR — {str(e)[:120]}
            </div>
            """, unsafe_allow_html=True)
            st.stop()

    # Update session counters
    st.session_state.active_incidents += 1
    st.session_state.last_incident_time = datetime.now().strftime("%H:%M:%S")

    # ── SAFE ACCESS HELPERS ──────────────────────────────────────────────────
    scam   = data.get("scam_assessment", {})
    meta   = data.get("incident_metadata", {})
    med    = data.get("extracted_medical_entities", {})
    hosp   = data.get("hospital_alert", {})
    queue  = data.get("priority_queue", {})
    disp   = data.get("dispatch_recommendation", {})
    hazards= data.get("environmental_hazards", [])

    # ── 1. SCAM PATH ─────────────────────────────────────────────────────────
    if scam.get("is_suspected_scam", False):
        scam_prob = scam.get("final_scam_probability", 0) * 100
        st.markdown("""
        <div class="banner-scam">
            &#9888;&nbsp; SCAM ALERT — POTENTIAL FRAUDULENT CALL — DO NOT DISPATCH &nbsp;&#9888;
        </div>
        """, unsafe_allow_html=True)

        bar_width = f"{scam_prob:.0f}%"
        indicators = scam.get("scam_indicators", [])
        indicators_html = "".join(
            f'<div class="list-item-red">&#9658; {i}</div>' for i in indicators
        ) if indicators else '<div class="list-item">No specific indicators captured.</div>'

        st.markdown(f"""
        <div class="panel-warning">
            <div class="panel-title">&#9888; Scam Assessment</div>
            <div class="metrics-grid cols-3">
                <div class="metric-card">
                    <div class="metric-label">Scam Probability</div>
                    <div class="metric-value-yellow">{scam_prob:.0f}%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Gemini Score</div>
                    <div class="metric-value-yellow">{scam.get('gemini_scam_score', 0)*100:.0f}%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">NLP Score</div>
                    <div class="metric-value-yellow">{scam.get('nlp_scam_score', 0)*100:.0f}%</div>
                </div>
            </div>
            <div style="margin-top:0.8rem;">
                <div class="data-label" style="margin-bottom:0.3rem;">PROBABILITY BAR</div>
                <div class="prob-bar-track">
                    <div class="prob-bar-fill" style="width:{bar_width};"></div>
                </div>
            </div>
        </div>

        <div class="panel-critical">
            <div class="panel-title">&#9658; Scam Indicators</div>
            {indicators_html}
        </div>

        <div class="metrics-grid cols-3">
            <div class="metric-card">
                <div class="metric-label">Caller Location</div>
                <div class="metric-value" style="font-size:1em;">{location_input or "TRACE REQUIRED"}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Dispatch Status</div>
                <div class="metric-value-red">HOLD</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Recommended Action</div>
                <div class="metric-value-yellow" style="font-size:0.9em;">ALERT LAW ENF.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("RAW AI OUTPUT  [CLASSIFIED]", expanded=False):
            st.json(data)

        st.stop()

    # ── 2. PRIORITY BANNER ───────────────────────────────────────────────────
    priority = meta.get("priority_level", "CODE_GREEN")
    if priority == "CODE_RED":
        st.markdown("""
        <div class="banner-red">
            &#9632;&nbsp; CODE RED — CRITICAL EMERGENCY — IMMEDIATE DISPATCH REQUIRED &nbsp;&#9632;
        </div>
        """, unsafe_allow_html=True)
    elif priority == "CODE_ORANGE":
        st.markdown("""
        <div class="banner-orange">
            &#9650;&nbsp; CODE ORANGE — URGENT — EXPEDITE DISPATCH &nbsp;&#9650;
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="banner-green">
            &#9679;&nbsp; CODE GREEN — NON-CRITICAL — STANDARD RESPONSE &nbsp;&#9679;
        </div>
        """, unsafe_allow_html=True)

    # ── 3. HUMAN VERIFICATION FLAG ───────────────────────────────────────────
    if data.get("requires_human_verification", False):
        st.markdown("""
        <div class="banner-verify">
            &#9888;&nbsp; HUMAN VERIFICATION REQUIRED — DISPATCH PENDING OPERATOR CONFIRMATION &nbsp;&#9888;
        </div>
        """, unsafe_allow_html=True)

    # ── 4. INCIDENT OVERVIEW ─────────────────────────────────────────────────
    victims    = meta.get("estimated_victims", 0)
    location   = location_input or meta.get("location_description") or "UNKNOWN"
    confidence = meta.get("confidence_score", 0) * 100
    v_color    = "metric-value-red" if victims > 1 else "metric-value"
    c_color    = "metric-value" if confidence >= 85 else "metric-value-orange"

    st.markdown(f"""
    <div class="panel">
        <div class="panel-title">&#9632; Incident Overview</div>
        <div class="metrics-grid cols-3">
            <div class="metric-card">
                <div class="metric-label">Victims Involved</div>
                <div class="{v_color}">{victims}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Incident Location</div>
                <div class="metric-value" style="font-size:0.95em; word-break:break-word;">{location}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">AI Confidence Score</div>
                <div class="{c_color}">{confidence:.0f}%</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 5. PATIENT ASSESSMENT ────────────────────────────────────────────────
    condition    = med.get("suspected_primary_condition") or "Unknown"
    consciousness= med.get("consciousness_level") or "Unknown"
    respiratory  = med.get("respiratory_estimate") or "Unknown"

    crit_words  = ["unresponsive", "unconscious", "cardiac", "arrest", "severe", "hemorrhage", "critical"]
    is_crit_con = any(w in condition.lower() for w in crit_words)
    is_crit_con2= any(w in consciousness.lower() for w in ["unresponsive", "unconscious"])
    panel_cls   = "panel-critical" if is_crit_con else "panel"
    cond_color  = "dv-red" if is_crit_con else "dv-orange"
    cons_color  = "dv-red" if is_crit_con2 else "dv-orange"

    st.markdown(f"""
    <div class="{panel_cls}">
        <div class="panel-title">&#9632; Patient Assessment</div>
        <div class="metrics-grid cols-3">
            <div class="metric-card">
                <div class="metric-label">Suspected Condition</div>
                <div class="{cond_color}" style="font-size:1em; margin-top:0.4rem; word-break:break-word;">{condition}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Consciousness Level</div>
                <div class="{cons_color}" style="font-size:1em; margin-top:0.4rem;">{consciousness}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Respiratory Status</div>
                <div class="dv-orange" style="font-size:1em; margin-top:0.4rem;">{respiratory}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 6. HOSPITAL ALERT ────────────────────────────────────────────────────
    hosp_name    = hosp.get("name", "Unknown")
    hosp_city    = hosp.get("city", "")
    hosp_dist    = hosp.get("distance_km", 0.0)
    hosp_eta     = hosp.get("eta_minutes", 0)
    hosp_bays    = hosp.get("available_bays", 0)
    hosp_surgeons= hosp.get("surgeons_on_call", [])
    hosp_prep    = hosp.get("preparation_instructions", "")

    facility_str  = hosp_name if (not hosp_city or hosp_city == "Unknown") else f"{hosp_name} — {hosp_city}"
    bays_color    = "dv-green" if hosp_bays > 0 else "dv-red"
    surgeons_html = "".join(f'<div class="list-item">&#9658; {s}</div>' for s in hosp_surgeons) if hosp_surgeons else '<div class="list-item" style="color:#444;">—</div>'
    prep_html     = f'<div class="prep-box"><div class="prep-label">&#9658; Preparation Instructions</div><div class="prep-text">{hosp_prep}</div></div>' if hosp_prep else ""

    st.markdown(f"""
    <div class="panel">
        <div class="panel-title">&#9632; Hospital Alert — Receiving Facility</div>
        <div class="two-col">
            <div>
                <div class="data-table">
                    <div class="data-row">
                        <span class="data-label">Facility Name</span>
                        <span class="dv">{facility_str}</span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">Distance</span>
                        <span class="dv">{hosp_dist:.1f} km</span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">ETA</span>
                        <span class="dv-orange">{hosp_eta} minutes</span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">Available Bays</span>
                        <span class="{bays_color}">{hosp_bays}</span>
                    </div>
                </div>
                {prep_html}
            </div>
            <div>
                <div class="sub-label">&#9632; Surgeons on Call</div>
                {surgeons_html}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 7. PRIORITY QUEUE ────────────────────────────────────────────────────
    q_pos    = queue.get("queue_position", 1)
    q_total  = queue.get("total_active_incidents", 1)
    q_amb    = queue.get("ambulances_available", 0)
    q_reason = queue.get("priority_reason", "—")
    pos_color= "metric-value-red" if q_pos == 1 else "metric-value"
    amb_color= "metric-value" if q_amb > 0 else "metric-value-red"

    st.markdown(f"""
    <div class="panel">
        <div class="panel-title">&#9632; Priority Queue — Dispatch Status</div>
        <div class="metrics-grid cols-3">
            <div class="metric-card">
                <div class="metric-label">Queue Position</div>
                <div class="{pos_color}">#{q_pos} / {q_total}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Ambulances Available</div>
                <div class="{amb_color}">{q_amb}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Priority Reason</div>
                <div class="metric-value" style="font-size:0.85em; word-break:break-word;">{q_reason}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 8. DISPATCH RECOMMENDATION ──────────────────────────────────────────
    equipment  = disp.get("equipment_loadout", [])
    specialists= disp.get("required_specialists", [])
    equip_html = "".join(
        f'<div class="list-item">&#9632; {item}</div>' for item in equipment
    ) if equipment else '<div class="list-item" style="color:#555;">Standard kit only</div>'
    spec_html  = "".join(
        f'<div class="list-item">&#9658; {s}</div>' for s in specialists
    ) if specialists else '<div class="list-item" style="color:#555;">No specialists required</div>'

    st.markdown(f"""
    <div class="panel">
        <div class="panel-title">&#9632; Dispatch Recommendation</div>
        <div class="two-col">
            <div>
                <div class="sub-label">&#9632; Equipment Loadout</div>
                {equip_html}
            </div>
            <div>
                <div class="sub-label">&#9632; Required Specialists</div>
                {spec_html}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 9. ENVIRONMENTAL HAZARDS ─────────────────────────────────────────────
    if hazards:
        haz_html = "".join(
            f'<div class="list-item-orange">&#9888; {h}</div>' for h in hazards
        )
        st.markdown(f"""
        <div class="panel-critical">
            <div class="panel-title">&#9888; Environmental Hazards — Scene Alert</div>
            {haz_html}
        </div>
        """, unsafe_allow_html=True)

    # ── 10. SCAM ASSESSMENT (partial / low probability) ──────────────────────
    scam_prob_raw = scam.get("final_scam_probability", 0)
    if scam_prob_raw > 0.1:
        scam_pct   = scam_prob_raw * 100
        gem_pct    = scam.get("gemini_scam_score", 0) * 100
        nlp_pct    = scam.get("nlp_scam_score", 0) * 100
        bar_w      = f"{scam_pct:.0f}%"
        indicators = scam.get("scam_indicators", [])
        ind_html   = "".join(
            f'<div class="list-item-orange">&#9658; {i}</div>' for i in indicators
        ) if indicators else ""

        st.markdown(f"""
        <div class="panel-warning">
            <div class="panel-title">&#9888; Scam Assessment — Low Probability Signal</div>
            <div class="metrics-grid cols-3">
                <div class="metric-card">
                    <div class="metric-label">Final Probability</div>
                    <div class="metric-value-yellow">{scam_pct:.1f}%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Gemini Score</div>
                    <div class="metric-value-yellow">{gem_pct:.1f}%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">NLP Score</div>
                    <div class="metric-value-yellow">{nlp_pct:.1f}%</div>
                </div>
            </div>
            <div style="margin-top:0.6rem;">
                <div class="data-label" style="margin-bottom:0.25rem;">SCAM PROBABILITY</div>
                <div class="prob-bar-track">
                    <div class="prob-bar-fill" style="width:{bar_w};"></div>
                </div>
            </div>
            {ind_html}
        </div>
        """, unsafe_allow_html=True)

    # ── 11. RAW JSON ─────────────────────────────────────────────────────────
    with st.expander("RAW AI OUTPUT  [CLASSIFIED]", expanded=False):
        st.json(data)
