import streamlit as st
import requests
import os
import json
from datetime import datetime
import folium
import streamlit.components.v1 as components
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Zero-Minute Dispatch",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Session State Init ─────────────────────────────────────────────────────────
if "incidents" not in st.session_state:
    st.session_state.incidents = []
if "total_today" not in st.session_state:
    st.session_state.total_today = 0
if "active_incidents" not in st.session_state:
    st.session_state.active_incidents = 0
if "scams_detected" not in st.session_state:
    st.session_state.scams_detected = 0
if "hospital_resources" not in st.session_state:
    st.session_state.hospital_resources = {
        "Hôpital Charles Nicolle": {
            "city": "Tunis", "trauma_bays": 4, "ambulances": 8,
            "surgeons": 5, "status": "OPERATIONAL"
        },
        "Hôpital Habib Thameur": {
            "city": "Tunis", "trauma_bays": 3, "ambulances": 6,
            "surgeons": 3, "status": "OPERATIONAL"
        },
        "Hôpital Militaire de Tunis": {
            "city": "Tunis", "trauma_bays": 5, "ambulances": 10,
            "surgeons": 7, "status": "OPERATIONAL"
        },
        "Clinique Les Oliviers": {
            "city": "Tunis", "trauma_bays": 2, "ambulances": 4,
            "surgeons": 2, "status": "OPERATIONAL"
        }
    }
if "last_report" not in st.session_state:
    st.session_state.last_report = None
if "show_notification" not in st.session_state:
    st.session_state.show_notification = False
if "ambulances" not in st.session_state:
    st.session_state.ambulances = []
if "incident_markers" not in st.session_state:
    st.session_state.incident_markers = []
if "amb_counter" not in st.session_state:
    st.session_state.amb_counter = 0

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');

html, body, [class*="css"] {
    background-color: #0a0a0a !important;
    color: #e0e0e0 !important;
    font-family: 'Inter', sans-serif !important;
}
.stApp { background-color: #0a0a0a !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 !important; max-width: 100% !important; }

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #0a0a0a; }
::-webkit-scrollbar-thumb { background: #c0392b; border-radius: 2px; }

.navbar {
    background: #0d0d0d;
    border-bottom: 1px solid #1e1e1e;
    padding: 12px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.brand-name {
    font-size: 16px; font-weight: 800; letter-spacing: 4px;
    color: #fff; text-transform: uppercase;
}
.brand-sub { font-size: 10px; color: #888; letter-spacing: 2px; }
.stat-box {
    background: #111; border: 1px solid #1e1e1e;
    border-radius: 4px; padding: 6px 18px; text-align: center;
    min-width: 90px;
}
.stat-num { font-size: 22px; font-weight: 700; }
.stat-lbl { font-size: 9px; color: #888; letter-spacing: 2px; text-transform: uppercase; }
.stat-red { color: #e74c3c; }
.stat-gold { color: #f39c12; }
.stat-green { color: #27ae60; }
.stat-white { color: #ffffff; }
.live-badge {
    display: flex; align-items: center; gap: 6px;
    background: #0d0d0d; border: 1px solid #1a3a1a;
    padding: 5px 12px; border-radius: 4px;
}
.live-dot {
    width: 8px; height: 8px; background: #2ecc71;
    border-radius: 50%; animation: blink 1.2s infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }
.live-text { font-size: 12px; color: #2ecc71; font-weight: 700; letter-spacing: 2px; }

.ticker-wrap {
    background: #c0392b; padding: 7px 0;
    overflow: hidden; white-space: nowrap;
    border-bottom: 1px solid #1e1e1e;
}
.ticker-inner {
    display: inline-block;
    animation: marquee 30s linear infinite;
}
.ticker-inner span { color: #fff; font-size: 11px; font-weight: 600; margin: 0 30px; }
.ticker-inner span.sep { color: rgba(255,255,255,0.4); margin: 0 6px; }
@keyframes marquee {
    0% { transform: translateX(0); }
    100% { transform: translateX(-50%); }
}

.section-header {
    padding: 10px 14px;
    background: #0d0d0d;
    border-bottom: 1px solid #1a1a1a;
    font-size: 10px; font-weight: 700;
    color: #c0392b; text-transform: uppercase; letter-spacing: 2px;
    display: flex; align-items: center; gap: 8px;
}

.incident-card {
    padding: 12px 14px;
    border-bottom: 1px solid #161616;
    transition: background .15s;
}
.incident-card:hover { background: #111; }
.incident-card.code-red { border-left: 3px solid #e74c3c; }
.incident-card.code-orange { border-left: 3px solid #f39c12; }
.incident-card.code-green { border-left: 3px solid #27ae60; }
.incident-card.scam { border-left: 3px solid #f39c12; background: #0f0d00; }
.inc-header { display: flex; justify-content: space-between; margin-bottom: 5px; }
.inc-title { font-size: 12px; font-weight: 600; color: #ddd; flex: 1; }
.inc-badge {
    font-size: 9px; font-weight: 700; padding: 2px 7px;
    border-radius: 2px; letter-spacing: 1px; white-space: nowrap; margin-left: 8px;
}
.badge-red { background: #3d1010; color: #e74c3c; border: 1px solid #c0392b; }
.badge-orange { background: #2d2000; color: #f39c12; border: 1px solid #d68910; }
.badge-green { background: #0e1e0e; color: #27ae60; border: 1px solid #1e8449; }
.badge-scam { background: #2d2d00; color: #f39c12; border: 1px solid #d68910; }
.inc-meta { font-size: 10px; color: #555; display: flex; gap: 10px; margin-top: 5px; }

.hospital-card {
    background: #0d0d0d; border: 1px solid #1a1a1a;
    border-radius: 4px; margin: 10px 14px; padding: 12px;
}
.hosp-name { font-size: 12px; font-weight: 700; color: #ddd; margin-bottom: 8px; }
.hosp-city { font-size: 10px; color: #555; margin-left: 6px; }
.resource-row {
    display: flex; justify-content: space-between;
    align-items: center; padding: 4px 0;
    border-bottom: 1px solid #111; font-size: 11px;
}
.resource-label { color: #888; }
.resource-val { font-weight: 700; font-family: 'Share Tech Mono', monospace; }
.resource-ok { color: #27ae60; }
.resource-warn { color: #f39c12; }
.resource-crit { color: #e74c3c; }
.hosp-status-ok { color: #27ae60; font-size: 9px; font-weight: 700; letter-spacing: 2px; }
.hosp-status-warn { color: #f39c12; font-size: 9px; font-weight: 700; letter-spacing: 2px; }

.code-red-banner {
    background: #1a0000; border: 1px solid #c0392b;
    border-radius: 6px; padding: 20px;
    text-align: center; margin: 16px;
    animation: pulse 1s infinite;
}
@keyframes pulse { 0%,100%{border-color:#c0392b} 50%{border-color:#e74c3c} }
.banner-title {
    font-size: 24px; font-weight: 900; color: #e74c3c;
    letter-spacing: 4px; text-transform: uppercase;
}
.banner-sub { font-size: 11px; color: #888; letter-spacing: 2px; margin-top: 4px; }

.scam-banner {
    background: #1a1a00; border: 1px solid #f39c12;
    border-radius: 6px; padding: 20px;
    text-align: center; margin: 16px;
}
.scam-title {
    font-size: 22px; font-weight: 900; color: #f39c12;
    letter-spacing: 3px; text-transform: uppercase;
}

.metric-card {
    background: #0d0d0d; border: 1px solid #1a1a1a;
    border-radius: 4px; padding: 14px; text-align: center;
}
.metric-val { font-size: 28px; font-weight: 800; font-family: 'Share Tech Mono', monospace; }
.metric-lbl { font-size: 9px; color: #555; text-transform: uppercase; letter-spacing: 2px; margin-top: 4px; }

.data-row {
    display: flex; justify-content: space-between;
    padding: 8px 0; border-bottom: 1px solid #111;
    font-size: 12px;
}
.data-label { color: #888; }
.data-val { color: #ddd; font-weight: 600; font-family: 'Share Tech Mono', monospace; }

.notification-popup {
    position: fixed; bottom: 80px; right: 20px;
    background: #111; border: 1px solid #c0392b;
    border-radius: 6px; padding: 14px 16px; width: 320px;
    z-index: 1000; box-shadow: 0 0 20px rgba(192,57,43,0.3);
    animation: slideUp .3s ease, fadeOut .4s ease 5s forwards;
}
@keyframes slideUp {
    from { transform: translateY(20px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
}
@keyframes fadeOut {
    from { opacity: 1; transform: translateY(0); }
    to { opacity: 0; transform: translateY(10px); visibility: hidden; }
}
.notif-label {
    font-size: 9px; font-weight: 700; letter-spacing: 2px;
    color: #e74c3c; text-transform: uppercase; margin-bottom: 6px;
}
.notif-title { font-size: 13px; color: #fff; font-weight: 700; margin-bottom: 4px; }
.notif-sub { font-size: 11px; color: #888; }

.upload-section {
    background: #0d0d0d; border: 1px solid #1a1a1a;
    border-radius: 6px; padding: 16px; margin: 16px;
}
.upload-label {
    font-size: 10px; color: #c0392b; font-weight: 700;
    letter-spacing: 2px; text-transform: uppercase; margin-bottom: 10px;
}

.prep-box {
    background: #0a1a0a; border-left: 3px solid #27ae60;
    padding: 10px 14px; border-radius: 3px; margin-top: 10px;
    font-size: 11px; color: #aaa; line-height: 1.6;
}
.prep-label {
    font-size: 9px; color: #27ae60; font-weight: 700;
    letter-spacing: 2px; text-transform: uppercase; margin-bottom: 6px;
}

.traffic-box {
    background: #0a0a1a; border-left: 3px solid #3498db;
    padding: 10px 14px; border-radius: 3px; margin-top: 8px;
    font-size: 11px; color: #aaa;
}
.traffic-label {
    font-size: 9px; color: #3498db; font-weight: 700;
    letter-spacing: 2px; text-transform: uppercase; margin-bottom: 6px;
}

.human-verify {
    background: #1a0a0a; border: 1px solid #c0392b;
    border-radius: 4px; padding: 10px 14px; margin: 10px 0;
    font-size: 11px; color: #e74c3c; font-weight: 700;
    text-align: center; letter-spacing: 2px; text-transform: uppercase;
}

.tag {
    display: inline-block; font-size: 9px; font-weight: 700;
    padding: 2px 8px; border-radius: 2px; letter-spacing: 1px;
    margin-right: 4px; margin-bottom: 4px;
}
.tag-red { background: #3d1010; color: #e74c3c; border: 1px solid #c0392b; }
.tag-blue { background: #0a1020; color: #3498db; border: 1px solid #2980b9; }
.tag-green { background: #0a1a0a; color: #27ae60; border: 1px solid #1e8449; }

/* ── INPUT ZONE WIDGETS ── */
[data-testid="stFileUploaderDropzone"] {
    background: #0d0d0d !important;
    border: 1px dashed #2d0000 !important;
    border-radius: 3px !important;
    padding: 14px !important;
    transition: border-color .2s ease !important;
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: #c0392b !important;
}
[data-testid="stFileUploaderDropzone"] span,
[data-testid="stFileUploaderDropzone"] p,
[data-testid="stFileUploaderDropzone"] small {
    color: #444 !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 11px !important;
    letter-spacing: 1px !important;
}
[data-testid="stFileUploaderDropzone"] svg {
    fill: #2d0000 !important;
    color: #2d0000 !important;
}
[data-testid="stFileUploader"] label {
    color: #c0392b !important;
    font-size: 9px !important;
    font-weight: 700 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    font-family: 'Share Tech Mono', monospace !important;
}

.stTextInput > label,
[data-testid="stWidgetLabel"] {
    color: #c0392b !important;
    font-size: 9px !important;
    font-weight: 700 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    font-family: 'Share Tech Mono', monospace !important;
}
.stTextInput > div > div > input {
    background: #0d0d0d !important;
    border: 1px solid #1e1e1e !important;
    border-radius: 3px !important;
    color: #ccc !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 12px !important;
    letter-spacing: 0.5px !important;
    padding: 10px 14px !important;
    transition: border-color .2s ease !important;
}
.stTextInput > div > div > input:focus {
    border-color: #c0392b !important;
    box-shadow: 0 0 0 1px rgba(192,57,43,0.25) !important;
    outline: none !important;
}
.stTextInput > div > div > input::placeholder {
    color: #333 !important;
    font-family: 'Share Tech Mono', monospace !important;
}

.stButton > button {
    background: #0d0d0d !important;
    color: #c0392b !important;
    border: 1px solid #c0392b !important;
    border-radius: 3px !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 12px !important;
    font-weight: 700 !important;
    letter-spacing: 4px !important;
    text-transform: uppercase !important;
    padding: 13px 0 !important;
    width: 100% !important;
    transition: background .15s ease, box-shadow .15s ease !important;
}
.stButton > button:hover {
    background: #c0392b !important;
    color: #fff !important;
    box-shadow: 0 0 18px rgba(192,57,43,0.35) !important;
}
.stButton > button:active {
    background: #96281b !important;
    color: #fff !important;
}
.stButton > button:disabled {
    background: #0d0d0d !important;
    color: #2a2a2a !important;
    border-color: #1a1a1a !important;
    cursor: not-allowed !important;
}
</style>
""", unsafe_allow_html=True)


# ── Helper functions ───────────────────────────────────────────────────────────
def get_badge_class(priority):
    if priority == "CODE_RED": return "badge-red", "CODE RED"
    if priority == "CODE_ORANGE": return "badge-orange", "CODE ORANGE"
    return "badge-green", "CODE GREEN"

def get_card_class(priority, is_scam):
    if is_scam: return "scam"
    if priority == "CODE_RED": return "code-red"
    if priority == "CODE_ORANGE": return "code-orange"
    return "code-green"

def get_resource_class(val, max_val):
    ratio = val / max_val if max_val > 0 else 0
    if ratio > 0.5: return "resource-ok"
    if ratio > 0.2: return "resource-warn"
    return "resource-crit"

# ── Map constants & helpers ────────────────────────────────────────────────────
HOSPITAL_COORDS = {
    "Hôpital Charles Nicolle":    {"lat": 36.8065, "lon": 10.1815},
    "Hôpital Habib Thameur":      {"lat": 36.8189, "lon": 10.1658},
    "Hôpital Militaire de Tunis": {"lat": 36.8321, "lon": 10.1897},
    "Clinique Les Oliviers":      {"lat": 36.8412, "lon": 10.2156},
}
HQ_LAT, HQ_LON = 36.8190, 10.1660
AMB_COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c"]
STEPS_PER_SEG = 12

def _lerp(p1, p2, steps):
    return [[p1[0] + (p2[0] - p1[0]) * i / steps,
             p1[1] + (p2[1] - p1[1]) * i / steps] for i in range(steps + 1)]

def build_route(origin, waypoint, dest, steps=STEPS_PER_SEG):
    return _lerp(origin, waypoint, steps) + _lerp(waypoint, dest, steps)[1:]

def next_amb_color():
    used = {a["color"] for a in st.session_state.ambulances if a["status"] != "ARRIVED"}
    for c in AMB_COLORS:
        if c not in used:
            return c
    return AMB_COLORS[st.session_state.amb_counter % len(AMB_COLORS)]

def dashboard_geocode(text):
    if not text:
        return None, None
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": text + " Tunisia", "format": "json", "limit": 1},
            headers={"User-Agent": "ZeroMinuteDispatch/1.0"},
            timeout=4
        )
        res = r.json()
        if res:
            return float(res[0]["lat"]), float(res[0]["lon"])
    except Exception:
        pass
    return None, None


def get_tomtom_route_points(origin_lat, origin_lon, dest_lat, dest_lon):
    """Fetch real road geometry from TomTom. Returns list of [lat, lon] pairs."""
    key = os.getenv("TOMTOM_API_KEY")
    url = (
        f"https://api.tomtom.com/routing/1/calculateRoute/"
        f"{origin_lat},{origin_lon}:{dest_lat},{dest_lon}/json"
    )
    params = {"key": key, "traffic": "true", "travelMode": "car"}
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        points = data["routes"][0]["legs"][0]["points"]
        return [[p["latitude"], p["longitude"]] for p in points]
    except Exception:
        return [[origin_lat, origin_lon], [dest_lat, dest_lon]]


def build_ticker():
    if not st.session_state.incidents:
        return "■ ZERO-MINUTE DISPATCH ONLINE &nbsp;&nbsp;&nbsp; ■ CIVIL PROTECTION OPS ACTIVE &nbsp;&nbsp;&nbsp; ■ AI PIPELINE READY &nbsp;&nbsp;&nbsp; ■ AWAITING INCIDENTS &nbsp;&nbsp;&nbsp;" * 2
    items = ""
    for inc in st.session_state.incidents[-5:]:
        if inc["is_scam"]:
            items += f'<span>⚠ SCAM DETECTED — {inc["location"]} — {inc["time"]}</span><span class="sep">■</span>'
        else:
            items += f'<span>🚨 {inc["priority"]} — {inc["condition"][:40]} — {inc["location"]} — {inc["time"]}</span><span class="sep">■</span>'
    return items * 2


# ── NAVBAR ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="navbar">
    <div>
        <div class="brand-name">🚨 Zero-Minute Dispatch</div>
        <div class="brand-sub">CIVIL PROTECTION COMMAND CENTER — AI TRIAGE SYSTEM</div>
    </div>
    <div style="display:flex;gap:10px;">
        <div class="stat-box">
            <div class="stat-num stat-red">{st.session_state.active_incidents}</div>
            <div class="stat-lbl">Active</div>
        </div>
        <div class="stat-box">
            <div class="stat-num stat-white">{st.session_state.total_today}</div>
            <div class="stat-lbl">Today</div>
        </div>
        <div class="stat-box">
            <div class="stat-num stat-gold">{st.session_state.scams_detected}</div>
            <div class="stat-lbl">Scams</div>
        </div>
    </div>
    <div class="live-badge">
        <div class="live-dot"></div>
        <div class="live-text">LIVE</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── TICKER ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="ticker-wrap">
    <div class="ticker-inner">{build_ticker()}</div>
</div>
""", unsafe_allow_html=True)

# ── THREE COLUMN LAYOUT ────────────────────────────────────────────────────────
col_left, col_mid, col_right = st.columns([1.2, 2, 1.2])

# ══════════════════════════════════════════════════════════════════════════════
# LEFT COLUMN — Incident Log
# ══════════════════════════════════════════════════════════════════════════════
with col_left:
    st.markdown('<div class="section-header">■ INCIDENT LOG — REAL-TIME</div>', unsafe_allow_html=True)

    if not st.session_state.incidents:
        st.markdown("""
        <div style="padding:30px 14px;text-align:center;color:#333;font-size:12px;letter-spacing:2px;">
            NO INCIDENTS RECORDED<br>SYSTEM MONITORING...
        </div>
        """, unsafe_allow_html=True)
    else:
        for inc in st.session_state.incidents:
            card_class = get_card_class(inc["priority"], inc["is_scam"])
            if inc["is_scam"]:
                badge_html = '<span class="inc-badge badge-scam">SCAM</span>'
                title = "⚠ FALSE CALL DETECTED"
            else:
                badge_class, badge_text = get_badge_class(inc["priority"])
                badge_html = f'<span class="inc-badge {badge_class}">{badge_text}</span>'
                title = inc["condition"][:50] if inc["condition"] else "Unknown Condition"

            st.markdown(f"""
            <div class="incident-card {card_class}">
                <div class="inc-header">
                    <div class="inc-title">{title}</div>
                    {badge_html}
                </div>
                <div class="inc-meta">
                    <span>🕐 {inc["time"]}</span>
                    <span>📍 {inc["location"]}</span>
                    <span>👥 {inc["victims"]} victim(s)</span>
                </div>
                {'<div class="inc-meta"><span>🏥 ' + inc["hospital"] + '</span></div>' if not inc["is_scam"] else ''}
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MIDDLE COLUMN — Analysis + Results
# ══════════════════════════════════════════════════════════════════════════════
with col_mid:
    # Upload section
    st.markdown('<div class="section-header">■ INCIDENT INPUT — SCENE RECORDING</div>', unsafe_allow_html=True)

    up_col1, up_col2 = st.columns([3, 2])
    with up_col1:
        uploaded_file = st.file_uploader(
            "Scene Recording",
            type=["mp4", "mp3", "wav", "m4a", "ogg", "webm", "mpeg4"],
            label_visibility="visible"
        )
    with up_col2:
        location_input = st.text_input(
            "Incident Location",
            placeholder="Route Nationale 9, Tunis"
        )

    analyze_btn = st.button(
        "■  ANALYZE EMERGENCY SCENE  ■",
        type="primary",
        use_container_width=True
    )

    st.markdown('<div style="border-bottom:1px solid #1a1a1a;margin:16px 0;"></div>', unsafe_allow_html=True)

    # ── DISPATCH MAP ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">■ DISPATCH MAP — LIVE OPERATIONS</div>', unsafe_allow_html=True)

    active_ambs = [a for a in st.session_state.ambulances if a["status"] != "ARRIVED"]

    # Status bar + simulate button
    map_ctl1, map_ctl2 = st.columns([4, 1])
    with map_ctl2:
        sim_clicked = st.button(
            "▶ SIMULATE DISPATCH",
            use_container_width=True,
            disabled=not active_ambs,
            key="sim_btn"
        )
    with map_ctl1:
        if st.session_state.ambulances:
            parts = []
            for a in st.session_state.ambulances:
                pct = int(100 * a["step"] / a["total_steps"]) if a["total_steps"] > 0 else 100
                parts.append(
                    f'<span style="color:{a["color"]};font-family:monospace;font-size:10px;">'
                    f'{a["id"]} &nbsp;{a["status"]} &nbsp;{pct}%</span>'
                )
            st.markdown(" &nbsp;<span style='color:#333'>|</span>&nbsp; ".join(parts), unsafe_allow_html=True)

    if sim_clicked:
        for a in st.session_state.ambulances:
            if a["status"] == "ARRIVED":
                continue
            advance = max(1, int(a["total_steps"] * 0.08))
            a["step"] = min(a["step"] + advance, a["total_steps"])
            mid = a.get("mid_idx", a["total_steps"] // 2)
            if a["step"] >= a["total_steps"]:
                a["status"] = "ARRIVED"
            elif a["step"] > mid:
                a["status"] = "TO_HOSPITAL"
            elif a["step"] >= mid:
                a["status"] = "AT_SCENE"
            else:
                a["status"] = "EN_ROUTE"
        st.rerun()

    # Build map — dark ops theme
    # (using components.html + _repr_html_() means Jinja2 renders server-side;
    #  DivIcon, folium.Element, styled Tooltip are all safe here)
    from branca.element import Element as _BrEl
    m = folium.Map(
        location=[36.8190, 10.1660],
        zoom_start=13,
        tiles='cartodbdark_matter',
        attr='&copy; <a href="https://carto.com/">CartoDB</a>'
    )

    # ── Civil Protection HQ — dark red pulsing star ───────────────────────────
    hq_html = (
        '<div style="display:flex;flex-direction:column;align-items:center;'
        'transform:translate(-50%,-50%);">'
        '<div style="width:30px;height:30px;background:#6b0000;border-radius:50%;'
        'border:2px solid #c0392b;display:flex;align-items:center;justify-content:center;'
        'box-shadow:0 0 14px rgba(192,57,43,0.65);">'
        '<span style="color:#fff;font-size:17px;line-height:1;">&#9733;</span>'
        '</div>'
        '<span style="color:#c0392b;font-family:monospace;font-size:9px;font-weight:700;'
        'letter-spacing:2px;margin-top:3px;text-shadow:0 1px 4px #000;">HQ</span>'
        '</div>'
    )
    folium.Marker(
        location=[HQ_LAT, HQ_LON],
        popup=folium.Popup(
            '<div style="background:#0d0d0d;color:#e0e0e0;font-family:monospace;'
            'padding:10px 14px;border-left:3px solid #c0392b;min-width:185px;">'
            '<b style="color:#c0392b;font-size:11px;">&#9733; CIVIL PROTECTION HQ</b><br>'
            '<span style="color:#555;font-size:9px;">Command &amp; Dispatch Centre — Tunis</span>'
            '</div>',
            max_width=240
        ),
        icon=folium.DivIcon(html=hq_html, icon_size=(72, 56), icon_anchor=(36, 28))
    ).add_to(m)

    # ── Hospital markers — dark square with red cross ─────────────────────────
    for h_name, h_coords in HOSPITAL_COORDS.items():
        res = st.session_state.hospital_resources.get(h_name, {})
        short_name = h_name.replace("H\u00f4pital ", "").replace("Clinique ", "")[:16]
        popup_html = (
            f'<div style="background:#0d0d0d;color:#e0e0e0;font-family:monospace;'
            f'padding:10px 14px;border-left:3px solid #8b0000;min-width:200px;">'
            f'<b style="color:#c0392b;font-size:10px;">&#10010; {h_name}</b><br>'
            f'<div style="color:#666;font-size:9px;margin-top:5px;">'
            f'Bays: <b style="color:#ddd;">{res.get("trauma_bays","?")}</b>'
            f'&nbsp;|&nbsp;Surgeons: <b style="color:#ddd;">{res.get("surgeons","?")}</b>'
            f'</div>'
            f'<div style="color:#2ecc71;font-size:8px;margin-top:3px;letter-spacing:1px;">'
            f'{res.get("status","?")}</div>'
            f'</div>'
        )
        hosp_html = (
            f'<div style="display:flex;flex-direction:column;align-items:center;'
            f'transform:translate(-50%,-50%);">'
            f'<div style="width:20px;height:20px;background:#120000;'
            f'border:1.5px solid #8b0000;display:flex;align-items:center;justify-content:center;">'
            f'<span style="color:#c0392b;font-size:12px;line-height:1;">&#10010;</span>'
            f'</div>'
            f'<span style="color:#484848;font-family:monospace;font-size:7.5px;'
            f'margin-top:2px;white-space:nowrap;letter-spacing:0.5px;">{short_name}</span>'
            f'</div>'
        )
        folium.Marker(
            location=[h_coords["lat"], h_coords["lon"]],
            popup=folium.Popup(popup_html, max_width=250),
            icon=folium.DivIcon(html=hosp_html, icon_size=(92, 44), icon_anchor=(46, 22))
        ).add_to(m)

    # ── Incident markers — pulsing circle (radius 12, fill_opacity 0.4) ───────
    for inc_m in st.session_state.incident_markers:
        badge_col = "#e74c3c" if inc_m["priority"] == "CODE_RED" else "#f39c12"
        popup_html = (
            f'<div style="background:#0d0d0d;color:#e0e0e0;font-family:monospace;'
            f'padding:10px 14px;border-left:3px solid {badge_col};min-width:190px;">'
            f'<b style="color:{badge_col};font-size:11px;">{inc_m["id"]}</b>'
            f'<span style="color:#444;font-size:8px;margin-left:6px;">{inc_m["priority"]}</span><br>'
            f'<span style="color:#999;font-size:9px;">{inc_m["condition"][:60]}</span><br>'
            f'<div style="color:#555;font-size:8px;margin-top:4px;">'
            f'Victims: {inc_m["victims"]} &nbsp;&bull;&nbsp; {inc_m["time"]}'
            f'</div></div>'
        )
        folium.CircleMarker(
            location=[inc_m["lat"], inc_m["lon"]],
            radius=12,
            color=badge_col,
            weight=2,
            fill=True,
            fill_color=badge_col,
            fill_opacity=0.4,
            popup=folium.Popup(popup_html, max_width=260)
        ).add_to(m)
        folium.CircleMarker(
            location=[inc_m["lat"], inc_m["lon"]],
            radius=5,
            color=badge_col,
            fill=True,
            fill_color=badge_col,
            fill_opacity=1.0
        ).add_to(m)

    # ── Ambulance routes (real road geometry) + pulsing marker + tooltip ────────
    for a in st.session_state.ambulances:
        # Support both old straight-line entries and new road-geometry entries
        route_pts = a.get("route_points", a.get("route", []))
        if not route_pts:
            continue
        hosp_short = a["hospital_name"].replace("H\u00f4pital ", "").replace("Clinique ", "")[:14]
        pct = int(100 * a["step"] / a["total_steps"]) if a["total_steps"] > 0 else 100
        going_to_scene = a["status"] in ("EN_ROUTE", "AT_SCENE", "RESPONDING")
        dest_label = "&#10132; SCENE" if going_to_scene else "&#10132; HOSP"

        # Ghost full-route dashed line (real road geometry)
        folium.PolyLine(
            locations=route_pts,
            color=a["color"], weight=2, opacity=0.2, dash_array="6 6"
        ).add_to(m)
        # Solid travelled portion
        if a["step"] > 0:
            folium.PolyLine(
                locations=route_pts[:a["step"] + 1],
                color=a["color"], weight=3, opacity=0.8, dash_array="8"
            ).add_to(m)

        # Ambulance position — pulsing CircleMarker
        pos = route_pts[a["step"]]
        folium.CircleMarker(
            location=pos,
            radius=8,
            color=a["color"],
            weight=2,
            fill=True,
            fill_color=a["color"],
            fill_opacity=0.85,
            popup=folium.Popup(
                f'<div style="background:#0d0d0d;color:#e0e0e0;font-family:monospace;'
                f'padding:10px 14px;border-left:3px solid {a["color"]};min-width:190px;">'
                f'<b style="color:{a["color"]};font-size:11px;">{a["id"]}</b><br>'
                f'<div style="color:#888;font-size:9px;margin-top:4px;">'
                f'Status: {a["status"]} ({pct}%)</div>'
                f'<div style="color:#888;font-size:9px;">Dest: {a["hospital_name"]}</div>'
                f'<div style="color:#888;font-size:9px;">Inc: {a["incident_id"]}</div>'
                f'<div style="color:#555;font-size:8px;margin-top:3px;">'
                f'{a["condition"][:45]}</div>'
                f'</div>',
                max_width=250
            )
        ).add_to(m)

        # Floating DivIcon label above the circle
        tip_html = (
            f'<div style="background:#090909;border:1px solid #1e1e1e;'
            f'border-left:2px solid {a["color"]};padding:3px 7px;'
            f'font-family:monospace;white-space:nowrap;">'
            f'<div style="color:{a["color"]};font-size:8px;font-weight:700;">{a["id"]}</div>'
            f'<div style="color:#666;font-size:7px;">{dest_label}&nbsp;{pct}%</div>'
            f'</div>'
        )
        folium.Marker(
            location=pos,
            icon=folium.DivIcon(
                html=tip_html,
                icon_size=(88, 32),
                icon_anchor=(44, 48)  # bottom-centre of label sits 16px above circle
            )
        ).add_to(m)

    # ── In-map legend — bottom-left overlay (safe: rendered via _repr_html_()) ─
    if st.session_state.ambulances:
        rows_html = "".join(
            f'<div style="display:flex;align-items:center;gap:7px;margin-bottom:5px;">'
            f'<div style="width:10px;height:10px;border-radius:50%;background:{ab["color"]};'
            f'box-shadow:0 0 5px {ab["color"]};flex-shrink:0;"></div>'
            f'<span style="font-size:9px;color:#aaa;">{ab["id"]} &mdash; {ab["status"]}</span>'
            f'</div>'
            for ab in st.session_state.ambulances
        )
        legend_el = (
            '<div style="position:absolute;bottom:28px;left:10px;z-index:9999;'
            'background:rgba(9,9,9,0.93);border:1px solid #1e1e1e;'
            'border-left:3px solid #c0392b;padding:8px 12px;font-family:monospace;">'
            '<div style="font-size:8px;color:#c0392b;letter-spacing:2px;font-weight:700;'
            'text-transform:uppercase;margin-bottom:7px;">ACTIVE UNITS</div>'
            + rows_html +
            '</div>'
        )
        m.get_root().html.add_child(_BrEl(legend_el))

    # Render map
    components.html(m._repr_html_(), height=420, scrolling=False)

    st.markdown('<div style="border-bottom:1px solid #1a1a1a;margin:8px 0 16px 0;"></div>', unsafe_allow_html=True)

    # ── Analysis (streaming) ──
    if uploaded_file and analyze_btn:
        files     = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        form_data = {"location": location_input} if location_input else {}

        stream_placeholder = st.empty()
        data = None

        with st.spinner("🛰 AI pipeline initializing..."):
            try:
                with requests.post(
                    "http://localhost:8000/analyze/stream",
                    files=files,
                    data=form_data or None,
                    stream=True,
                    timeout=300
                ) as resp:
                    raw_output = ""
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        decoded = line.decode("utf-8")
                        if not decoded.startswith("data: "):
                            continue
                        chunk = decoded[6:]
                        if chunk.startswith("[DONE]"):
                            try:
                                data = json.loads(chunk[6:])
                            except Exception as parse_err:
                                st.error(f"Failed to parse AI response: {parse_err}")
                                st.stop()
                            break
                        else:
                            raw_output += chunk
                            stream_placeholder.markdown(
                                f'<div style="background:#0d0d0d;border:1px solid #1a1a1a;'
                                f'padding:12px 14px;font-family:monospace;font-size:11px;'
                                f'color:#27ae60;min-height:64px;line-height:1.6;">'
                                f'<div style="color:#c0392b;font-size:8px;letter-spacing:2px;'
                                f'font-weight:700;margin-bottom:8px;">■ AI GENERATING TRIAGE REPORT...</div>'
                                f'{raw_output[-500:]}'
                                f'</div>',
                                unsafe_allow_html=True
                            )
            except Exception as e:
                st.error(f"Pipeline error: {e}")
                st.stop()

        stream_placeholder.empty()

        if data is None:
            st.error("No valid response received from AI pipeline")
            st.stop()

        st.session_state.last_report = data

        # ── Save incident to log ──
        is_scam      = data["scam_assessment"]["is_suspected_scam"]
        priority     = data["incident_metadata"]["priority_level"]
        condition    = data["extracted_medical_entities"]["suspected_primary_condition"] or "Unknown"
        hospital_name = (data.get("hospital_alert") or {}).get("name", "N/A")

        st.session_state.incidents.insert(0, {
            "time":     datetime.now().strftime("%H:%M:%S"),
            "priority": priority,
            "condition": condition,
            "location": location_input or data["incident_metadata"]["location_description"] or "Unknown",
            "victims":  data["incident_metadata"]["estimated_victims"],
            "hospital": hospital_name,
            "is_scam":  is_scam
        })

        # ── Update counters ──
        if is_scam:
            st.session_state.scams_detected += 1
        else:
            st.session_state.total_today += 1
            if priority == "CODE_RED":
                st.session_state.active_incidents += 1

            # Decrement hospital resources
            for hosp_name, resources in st.session_state.hospital_resources.items():
                if hosp_name in hospital_name or hospital_name in hosp_name:
                    if resources["trauma_bays"] > 0:
                        resources["trauma_bays"] -= 1
                    if resources["ambulances"] > 0:
                        resources["ambulances"] -= 1
                    if resources["surgeons"] > 0:
                        resources["surgeons"] -= 1
                    if resources["trauma_bays"] <= 1:
                        resources["status"] = "CRITICAL"
                    elif resources["trauma_bays"] <= 2:
                        resources["status"] = "STRAINED"

        # ── Create ambulance dispatch entry ──
        if not is_scam and priority in ("CODE_RED", "CODE_ORANGE"):
            inc_lat, inc_lon = dashboard_geocode(location_input)
            if not inc_lat:
                offset   = len(st.session_state.incident_markers) * 0.006
                inc_lat  = 36.8065 + offset
                inc_lon  = 10.1815 + offset * 0.5

            h_coords = HOSPITAL_COORDS.get(hospital_name, {"lat": 36.8065, "lon": 10.1815})
            inc_id   = f"INC-{len(st.session_state.incident_markers) + 1:03d}"

            st.session_state.incident_markers.append({
                "id":       inc_id,
                "lat":      inc_lat,
                "lon":      inc_lon,
                "priority": priority,
                "condition": condition,
                "victims":  data["incident_metadata"]["estimated_victims"],
                "time":     datetime.now().strftime("%H:%M:%S"),
            })

            st.session_state.amb_counter += 1
            amb_id = f"AMB-{st.session_state.amb_counter:03d}"
            h_lat  = h_coords["lat"]
            h_lon  = h_coords["lon"]

            leg1         = get_tomtom_route_points(HQ_LAT, HQ_LON, inc_lat, inc_lon)
            leg2         = get_tomtom_route_points(inc_lat, inc_lon, h_lat, h_lon)
            route_points = leg1 + leg2[1:]
            mid_idx      = len(leg1) - 1

            st.session_state.ambulances.append({
                "id":           amb_id,
                "color":        next_amb_color(),
                "hospital_name": hospital_name,
                "route_points": route_points,
                "mid_idx":      mid_idx,
                "step":         0,
                "total_steps":  len(route_points) - 1,
                "status":       "EN_ROUTE",
                "incident_id":  inc_id,
                "condition":    condition[:40],
            })

        st.session_state.show_notification = True
        st.rerun()

    # ── Show last report ──
    if st.session_state.last_report:
        data = st.session_state.last_report
        is_scam = data["scam_assessment"]["is_suspected_scam"]
        priority = data["incident_metadata"]["priority_level"]

        # Priority banner
        if is_scam:
            st.markdown("""
            <div class="scam-banner">
                <div class="scam-title">⚠ SCAM CALL DETECTED — DO NOT DISPATCH</div>
            </div>
            """, unsafe_allow_html=True)
        elif priority == "CODE_RED":
            st.markdown("""
            <div class="code-red-banner">
                <div class="banner-title">🔴 CODE RED — CRITICAL EMERGENCY</div>
                <div class="banner-sub">IMMEDIATE DISPATCH REQUIRED</div>
            </div>
            """, unsafe_allow_html=True)
        elif priority == "CODE_ORANGE":
            st.markdown("""
            <div style="background:#1a0f00;border:1px solid #f39c12;border-radius:6px;
                padding:20px;text-align:center;margin:16px;">
                <div style="font-size:22px;font-weight:900;color:#f39c12;letter-spacing:3px;">
                    🟠 CODE ORANGE — URGENT
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:#0a1a0a;border:1px solid #27ae60;border-radius:6px;
                padding:20px;text-align:center;margin:16px;">
                <div style="font-size:22px;font-weight:900;color:#27ae60;letter-spacing:3px;">
                    🟢 CODE GREEN — NON CRITICAL
                </div>
            </div>
            """, unsafe_allow_html=True)

        if is_scam:
            scam = data["scam_assessment"]
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-val" style="color:#f39c12;">{int(scam['final_scam_probability']*100)}%</div>
                    <div class="metric-lbl">Scam Probability</div>
                </div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-val" style="color:#e74c3c;">TRACE</div>
                    <div class="metric-lbl">Action Required</div>
                </div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-val" style="color:#888;">0</div>
                    <div class="metric-lbl">Dispatched</div>
                </div>""", unsafe_allow_html=True)

            if scam["scam_indicators"]:
                st.markdown("**Scam Indicators:**")
                for ind in scam["scam_indicators"]:
                    st.markdown(f'<span class="tag tag-red">■ {ind}</span>', unsafe_allow_html=True)

        else:
            # Metrics row
            meta = data["incident_metadata"]
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-val" style="color:#e74c3c;">{meta['estimated_victims']}</div>
                    <div class="metric-lbl">Victims Involved</div>
                </div>""", unsafe_allow_html=True)
            with c2:
                loc = location_input or meta.get("location_description") or "Unknown"
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-val" style="color:#ddd;font-size:14px;">{loc[:20]}</div>
                    <div class="metric-lbl">Incident Location</div>
                </div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-val" style="color:#27ae60;">{int(meta['confidence_score']*100)}%</div>
                    <div class="metric-lbl">AI Confidence</div>
                </div>""", unsafe_allow_html=True)

            st.markdown("---")

            # Patient assessment
            st.markdown('<div class="section-header">■ PATIENT ASSESSMENT</div>', unsafe_allow_html=True)
            med = data["extracted_medical_entities"]
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-size:10px;color:#888;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;">Suspected Condition</div>
                    <div style="font-size:12px;color:#e74c3c;font-weight:600;line-height:1.4;">{med['suspected_primary_condition']}</div>
                </div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-size:10px;color:#888;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;">Consciousness</div>
                    <div style="font-size:12px;color:#f39c12;font-weight:600;">{med['consciousness_level']}</div>
                </div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-size:10px;color:#888;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;">Respiratory</div>
                    <div style="font-size:12px;color:#3498db;font-weight:600;">{med['respiratory_estimate']}</div>
                </div>""", unsafe_allow_html=True)

            st.markdown("---")

            # Hospital alert
            hosp = data["hospital_alert"]
            traffic = hosp.get("traffic_route", {})
            st.markdown('<div class="section-header">■ HOSPITAL ALERT — RECEIVING FACILITY</div>', unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"""
                <div style="padding:10px 0;">
                    <div class="data-row"><span class="data-label">FACILITY</span><span class="data-val">{hosp['name']}</span></div>
                    <div class="data-row"><span class="data-label">CITY</span><span class="data-val">{hosp['city']}</span></div>
                    <div class="data-row"><span class="data-label">DISTANCE</span><span class="data-val">{hosp['distance_km']} km</span></div>
                    <div class="data-row"><span class="data-label">ETA</span><span class="data-val" style="color:#e74c3c;">{hosp['eta_minutes']} min</span></div>
                    <div class="data-row"><span class="data-label">AVAILABLE BAYS</span><span class="data-val" style="color:#27ae60;">{hosp['available_bays']}</span></div>
                </div>""", unsafe_allow_html=True)
            with c2:
                surgeons = hosp.get("surgeons_on_call", [])
                surgeon_html = "".join([f'<div style="font-size:11px;color:#aaa;padding:3px 0;">▶ {s}</div>' for s in surgeons])
                st.markdown(f"""
                <div style="padding:10px 0;">
                    <div style="font-size:10px;color:#888;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;">SURGEONS ON CALL</div>
                    {surgeon_html}
                </div>""", unsafe_allow_html=True)

            if hosp.get("preparation_instructions"):
                st.markdown(f"""
                <div class="prep-box">
                    <div class="prep-label">▶ Preparation Instructions</div>
                    {hosp['preparation_instructions']}
                </div>""", unsafe_allow_html=True)

            if traffic.get("traffic_condition"):
                st.markdown(f"""
                <div class="traffic-box">
                    <div class="traffic-label">▶ Traffic Status</div>
                    {traffic['traffic_condition']} — {traffic.get('travel_time_minutes', 0)} min travel time
                </div>""", unsafe_allow_html=True)

            st.markdown("---")

            # Dispatch
            st.markdown('<div class="section-header">■ DISPATCH RECOMMENDATION</div>', unsafe_allow_html=True)
            disp = data["dispatch_recommendation"]
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Equipment Loadout**")
                for item in disp["equipment_loadout"]:
                    st.markdown(f'<span class="tag tag-green">✓ {item}</span>', unsafe_allow_html=True)
            with c2:
                st.markdown("**Required Specialists**")
                for spec in disp["required_specialists"]:
                    st.markdown(f'<span class="tag tag-blue">▶ {spec}</span>', unsafe_allow_html=True)

            # Hazards
            hazards = data.get("environmental_hazards", [])
            if hazards:
                st.markdown("---")
                st.markdown('<div class="section-header">■ ENVIRONMENTAL HAZARDS</div>', unsafe_allow_html=True)
                for h in hazards:
                    st.markdown(f'<span class="tag tag-red">⚠ {h}</span>', unsafe_allow_html=True)

            # Priority queue
            pq = data.get("priority_queue", {})
            if pq:
                st.markdown("---")
                st.markdown('<div class="section-header">■ PRIORITY QUEUE — DISPATCH STATUS</div>', unsafe_allow_html=True)
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-val" style="color:#e74c3c;">#{pq.get('queue_position',1)}/{pq.get('total_active_incidents',1)}</div>
                        <div class="metric-lbl">Queue Position</div>
                    </div>""", unsafe_allow_html=True)
                with c2:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-val" style="color:#27ae60;">{pq.get('ambulances_available',3)}</div>
                        <div class="metric-lbl">Ambulances Available</div>
                    </div>""", unsafe_allow_html=True)
                with c3:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-val" style="color:#888;font-size:14px;">{pq.get('priority_reason','—')[:20]}</div>
                        <div class="metric-lbl">Priority Reason</div>
                    </div>""", unsafe_allow_html=True)

            # Human verification
            if data.get("requires_human_verification"):
                st.markdown("""
                <div class="human-verify">⚠ HUMAN VERIFICATION REQUIRED</div>
                """, unsafe_allow_html=True)

        # Raw output
        with st.expander("🔧 RAW AI OUTPUT [CLASSIFIED]"):
            st.json(data)

# ══════════════════════════════════════════════════════════════════════════════
# RIGHT COLUMN — Hospital Resources
# ══════════════════════════════════════════════════════════════════════════════
with col_right:
    st.markdown('<div class="section-header">■ HOSPITAL RESOURCES — LIVE</div>', unsafe_allow_html=True)

    for hosp_name, res in st.session_state.hospital_resources.items():
        bays_class = get_resource_class(res["trauma_bays"], 5)
        amb_class = get_resource_class(res["ambulances"], 10)
        surg_class = get_resource_class(res["surgeons"], 7)
        status_class = "hosp-status-ok" if res["status"] == "OPERATIONAL" else "hosp-status-warn"

        st.markdown(f"""
        <div class="hospital-card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <div>
                    <span class="hosp-name">{hosp_name.replace("Hôpital ","")}</span>
                    <span class="hosp-city">{res['city']}</span>
                </div>
                <span class="{status_class}">{res['status']}</span>
            </div>
            <div class="resource-row">
                <span class="resource-label">Trauma Bays</span>
                <span class="resource-val {bays_class}">{res['trauma_bays']}</span>
            </div>
            <div class="resource-row">
                <span class="resource-label">Ambulances</span>
                <span class="resource-val {amb_class}">{res['ambulances']}</span>
            </div>
            <div class="resource-row">
                <span class="resource-label">Surgeons</span>
                <span class="resource-val {surg_class}">{res['surgeons']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="section-header" style="margin-top:10px;">■ SESSION STATISTICS</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div style="padding:14px;">
        <div class="data-row">
            <span class="data-label">Total Incidents</span>
            <span class="data-val">{st.session_state.total_today}</span>
        </div>
        <div class="data-row">
            <span class="data-label">Active CODE RED</span>
            <span class="data-val" style="color:#e74c3c;">{st.session_state.active_incidents}</span>
        </div>
        <div class="data-row">
            <span class="data-label">Scams Detected</span>
            <span class="data-val" style="color:#f39c12;">{st.session_state.scams_detected}</span>
        </div>
        <div class="data-row">
            <span class="data-label">System Status</span>
            <span class="data-val" style="color:#27ae60;">OPERATIONAL</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Notification popup ─────────────────────────────────────────────────────────
if st.session_state.show_notification and st.session_state.incidents:
    last = st.session_state.incidents[0]
    if last["is_scam"]:
        notif_html = f"""
        <div id="notif-popup" class="notification-popup" style="border-color:#f39c12;">
            <div class="notif-label" style="color:#f39c12;">⚠ SCAM DETECTED</div>
            <div class="notif-title">FALSE CALL — DO NOT DISPATCH</div>
            <div class="notif-sub">📍 {last['location']} — {last['time']}</div>
        </div>
        <script>
            setTimeout(function(){{
                var el = document.getElementById('notif-popup');
                if(el) el.style.display = 'none';
            }}, 4000);
        </script>"""
    else:
        notif_html = f"""
        <div id="notif-popup" class="notification-popup">
            <div class="notif-label">🚨 NEW INCIDENT — {last['priority']}</div>
            <div class="notif-title">{last['condition'][:60]}</div>
            <div class="notif-sub">📍 {last['location']} — 👥 {last['victims']} victim(s) — {last['time']}</div>
        </div>
        <script>
            setTimeout(function(){{
                var el = document.getElementById('notif-popup');
                if(el) el.style.display = 'none';
            }}, 4000);
        </script>"""
    st.markdown(notif_html, unsafe_allow_html=True)
    st.session_state.show_notification = False