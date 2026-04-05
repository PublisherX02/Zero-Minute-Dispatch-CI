import streamlit as st
import requests
import os
import json
import base64
from datetime import datetime
import folium
from streamlit_folium import st_folium
import streamlit.components.v1 as components
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_URL = os.getenv("API_URL", "http://localhost:8000")

# ── Local logo images (base64-encoded so they work inside st.markdown HTML) ───
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _b64_img(filename):
    try:
        with open(os.path.join(_ROOT, filename), "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    except Exception:
        return ""

TUNISIA_LOGO = _b64_img("hd-tunisia-coat-of-arms-logo-png-701751694775519gxajn6tbdb.png")
CIVIL_LOGO   = _b64_img("Écusson_protection_civile,_Tunisie.svg.png")

st.set_page_config(page_title="Zero-Minute Dispatch", page_icon="🚨",
                   layout="wide", initial_sidebar_state="collapsed")

# ── Session State ──────────────────────────────────────────────────────────────
if "incidents"          not in st.session_state: st.session_state.incidents          = []
if "total_today"        not in st.session_state: st.session_state.total_today        = 0
if "active_incidents"   not in st.session_state: st.session_state.active_incidents   = 0
if "scams_detected"     not in st.session_state: st.session_state.scams_detected     = 0
if "last_report"        not in st.session_state: st.session_state.last_report        = None
if "show_notification"  not in st.session_state: st.session_state.show_notification  = False
if "show_modal"         not in st.session_state: st.session_state.show_modal         = False
if "ambulances"         not in st.session_state: st.session_state.ambulances         = []
if "incident_markers"   not in st.session_state: st.session_state.incident_markers   = []
if "amb_counter"        not in st.session_state: st.session_state.amb_counter        = 0
if "hospital_resources" not in st.session_state:
    st.session_state.hospital_resources = {
        "Hôpital Charles Nicolle":    {"city":"Tunis","trauma_bays":4,"trauma_bays_max":4,"ambulances":8,"ambulances_max":8,"surgeons":5,"surgeons_max":5,"status":"OPERATIONAL"},
        "Hôpital Habib Thameur":      {"city":"Tunis","trauma_bays":3,"trauma_bays_max":3,"ambulances":6,"ambulances_max":6,"surgeons":3,"surgeons_max":3,"status":"OPERATIONAL"},
        "Hôpital Militaire de Tunis": {"city":"Tunis","trauma_bays":5,"trauma_bays_max":5,"ambulances":10,"ambulances_max":10,"surgeons":7,"surgeons_max":7,"status":"OPERATIONAL"},
        "Clinique Les Oliviers":      {"city":"Tunis","trauma_bays":2,"trauma_bays_max":2,"ambulances":4,"ambulances_max":4,"surgeons":2,"surgeons_max":2,"status":"OPERATIONAL"},
    }

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');

/* ── APP BACKGROUND ── */
html, body {
    overflow: hidden !important;
    height: 100vh !important;
    color: #e0e0e0 !important;
    font-family: 'Inter', sans-serif !important;
}
.stApp {
    background:
        radial-gradient(ellipse at 30% 50%, rgba(192,57,43,0.03) 0%, transparent 60%),
        radial-gradient(ellipse at 70% 50%, rgba(52,152,219,0.03) 0%, transparent 60%),
        #0a0a0a !important;
    overflow: hidden !important;
    height: 100vh !important;
}
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 !important; max-width: 100% !important; overflow: hidden !important; }
section[data-testid="stMain"] { overflow: hidden !important; height: 100vh !important; }

/* ── CENTER COLUMN — must NOT clip the iframe that renders the folium map ── */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2),
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) > div:first-child {
    overflow-y: auto !important;
    overflow-x: hidden !important;
}
/* ── LEFT + RIGHT WIDTHS ── */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child,
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {
    min-width: 280px !important;
    max-width: 280px !important;
    flex: 0 0 280px !important;
    border-right: 1px solid #1a1a1a;
}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {
    border-right: none !important;
    border-left: 1px solid #1a1a1a;
}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) {
    flex: 1 1 0 !important;
    min-width: 0 !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2)::-webkit-scrollbar { width: 3px; }
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2)::-webkit-scrollbar-thumb { background: #3a0000; }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 3px; height: 3px; }
::-webkit-scrollbar-track { background: #0a0a0a; }
::-webkit-scrollbar-thumb { background: #8b0000; border-radius: 2px; }

/* ── NAVBAR ── */
.ops-navbar {
    height: 60px;
    background: #080808;
    border-bottom: 1px solid #1a1a1a;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 16px;
    flex-shrink: 0;
}
.logo-wrap { display: flex; align-items: center; gap: 10px; }
.logo-img {
    height: 38px; width: 38px; object-fit: contain;
    border-radius: 50%; background: rgba(255,255,255,0.06); padding: 3px;
    flex-shrink: 0;
}
.brand { display: flex; flex-direction: column; justify-content: center; }
.brand-name { font-size: 14px; font-weight: 800; letter-spacing: 4px; color: #fff; text-transform: uppercase; line-height: 1; }
.brand-sub { font-size: 8px; color: #555; letter-spacing: 2px; margin-top: 3px; }
.stat-row { display: flex; gap: 6px; }
.stat-box { background: #0d0d0d; border: 1px solid #1e1e1e; padding: 4px 12px; text-align: center; min-width: 66px; }
.stat-num { font-size: 18px; font-weight: 700; font-family: 'Share Tech Mono', monospace; line-height: 1; }
.stat-lbl { font-size: 7px; color: #555; letter-spacing: 2px; text-transform: uppercase; margin-top: 2px; }
.s-red { color: #e74c3c; } .s-white { color: #fff; } .s-gold { color: #f39c12; } .s-blue { color: #3498db; }
.live-badge { display: flex; align-items: center; gap: 5px; background: #050f05; border: 1px solid #1a3a1a; padding: 4px 10px; }
.live-dot { width: 7px; height: 7px; background: #2ecc71; border-radius: 50%; animation: blink 1.2s infinite; }
.live-text { font-size: 10px; color: #2ecc71; font-weight: 700; letter-spacing: 3px; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.25} }

/* ── TICKER ── */
.ticker-wrap {
    height: 28px; background: #8b0000;
    overflow: hidden; white-space: nowrap;
    display: flex; align-items: center;
    border-bottom: 1px solid #1e1e1e; flex-shrink: 0;
}
.ticker-inner { display: inline-block; animation: marquee 35s linear infinite; }
.ticker-inner span { color: #fff; font-size: 10px; font-weight: 600; margin: 0 28px; font-family: 'Share Tech Mono', monospace; letter-spacing: 1px; }
.ticker-inner span.sep { color: rgba(255,255,255,0.3); margin: 0 4px; }
@keyframes marquee { 0%{transform:translateX(0)} 100%{transform:translateX(-50%)} }

/* ── PANEL HEADER ── */
.panel-hdr {
    height: 28px; background: #080808; border-bottom: 1px solid #161616;
    display: flex; align-items: center; padding: 0 12px;
    font-size: 8px; font-weight: 700; color: #c0392b;
    letter-spacing: 3px; text-transform: uppercase; flex-shrink: 0;
    font-family: 'Share Tech Mono', monospace;
}

/* ── STREAMLIT MAP (folium) ── */
[data-testid="stIFrame"],
iframe {
    border: none !important;
    display: block !important;
    visibility: visible !important;
}
/* The component wrapper div that Streamlit wraps around components.html() */
[data-testid="stCustomComponentV1"] {
    display: block !important;
    min-height: 360px !important;
    overflow: visible !important;
}
[data-testid="stCustomComponentV1"] iframe {
    width: 100% !important;
    min-height: 360px !important;
    display: block !important;
}
.stFoliumChart { border: none !important; }

/* ── STREAMLIT WIDGETS ── */
[data-testid="stFileUploaderDropzone"] {
    background: #0a0a0a !important; border: 1px dashed #1e1e1e !important;
    border-radius: 2px !important; padding: 8px !important;
}
[data-testid="stFileUploaderDropzone"]:hover { border-color: #8b0000 !important; }
[data-testid="stFileUploaderDropzone"] span,
[data-testid="stFileUploaderDropzone"] p,
[data-testid="stFileUploaderDropzone"] small {
    color: #333 !important; font-family: 'Share Tech Mono', monospace !important;
    font-size: 10px !important; letter-spacing: 1px !important;
}
[data-testid="stFileUploaderDropzone"] svg { fill: #1e1e1e !important; }
[data-testid="stFileUploader"] label {
    color: #c0392b !important; font-size: 8px !important; font-weight: 700 !important;
    letter-spacing: 2px !important; text-transform: uppercase !important;
    font-family: 'Share Tech Mono', monospace !important;
}
.stTextInput > label, [data-testid="stWidgetLabel"] {
    color: #c0392b !important; font-size: 8px !important; font-weight: 700 !important;
    letter-spacing: 2px !important; text-transform: uppercase !important;
    font-family: 'Share Tech Mono', monospace !important;
}
.stTextInput > div > div > input {
    background: #0a0a0a !important; border: 1px solid #1a1a1a !important;
    border-radius: 2px !important; color: #bbb !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 11px !important; padding: 8px 10px !important;
}
.stTextInput > div > div > input:focus {
    border-color: #8b0000 !important; outline: none !important;
    box-shadow: 0 0 0 1px rgba(139,0,0,0.3) !important;
}
.stTextInput > div > div > input::placeholder { color: #2a2a2a !important; }
.stButton > button {
    background: #090909 !important; color: #c0392b !important;
    border: 1px solid #8b0000 !important; border-radius: 2px !important;
    font-family: 'Share Tech Mono', monospace !important; font-size: 10px !important;
    font-weight: 700 !important; letter-spacing: 3px !important;
    text-transform: uppercase !important; padding: 10px 0 !important;
    width: 100% !important; transition: all .15s !important;
}
.stButton > button:hover { background: #8b0000 !important; color: #fff !important; box-shadow: 0 0 12px rgba(139,0,0,0.4) !important; }
.stButton > button:active { background: #6b0000 !important; }
.stButton > button:disabled { background: #080808 !important; color: #222 !important; border-color: #111 !important; }

/* ── STREAM OUTPUT ── */
.stream-box {
    background: #040404; border: 1px solid #111;
    padding: 10px 12px; font-family: 'Share Tech Mono', monospace;
    font-size: 10px; color: #2ecc71; line-height: 1.7; overflow: hidden;
}
.stream-label { color: #c0392b; font-size: 7px; letter-spacing: 3px; font-weight: 700; margin-bottom: 6px; }

/* ── NOTIFICATIONS ── */
.notif-stack { position: fixed; bottom: 16px; right: 16px; z-index: 9998; display: flex; flex-direction: column-reverse; gap: 8px; }
.notif-card { background: #0d0d0d; border: 1px solid #c0392b; padding: 12px 14px; width: 300px; box-shadow: 0 0 20px rgba(192,57,43,0.25); animation: slideUp .3s ease, fadeOut .4s ease 5s forwards; }
.notif-card.scam { border-color: #f39c12; }
.notif-lbl { font-size: 8px; font-weight: 700; letter-spacing: 2px; color: #c0392b; text-transform: uppercase; margin-bottom: 5px; font-family: 'Share Tech Mono', monospace; }
.notif-lbl.scam { color: #f39c12; }
.notif-title { font-size: 12px; color: #fff; font-weight: 600; margin-bottom: 3px; }
.notif-sub { font-size: 10px; color: #666; }
@keyframes slideUp { from{transform:translateY(16px);opacity:0} to{transform:translateY(0);opacity:1} }
@keyframes fadeOut { from{opacity:1} to{opacity:0;visibility:hidden} }
[data-testid="stSpinner"] { color: #c0392b !important; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────
def get_resource_class(val, max_val):
    ratio = val / max_val if max_val > 0 else 0
    if ratio > 0.5: return "#27ae60"
    if ratio > 0.2: return "#f39c12"
    return "#e74c3c"

HOSPITAL_COORDS = {
    "Hôpital Charles Nicolle":    {"lat": 36.8065, "lon": 10.1815},
    "Hôpital Habib Thameur":      {"lat": 36.8189, "lon": 10.1658},
    "Hôpital Militaire de Tunis": {"lat": 36.8321, "lon": 10.1897},
    "Clinique Les Oliviers":      {"lat": 36.8412, "lon": 10.2156},
}
HQ_LAT, HQ_LON  = 36.8190, 10.1660
AMB_COLORS       = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c"]
STEPS_PER_SEG    = 12

def _lerp(p1, p2, steps):
    return [[p1[0]+(p2[0]-p1[0])*i/steps, p1[1]+(p2[1]-p1[1])*i/steps] for i in range(steps+1)]

def next_amb_color():
    used = {a["color"] for a in st.session_state.ambulances if a["status"] != "ARRIVED"}
    for c in AMB_COLORS:
        if c not in used: return c
    return AMB_COLORS[st.session_state.amb_counter % len(AMB_COLORS)]

def dashboard_geocode(text):
    if not text: return None, None
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search",
                         params={"q": text + " Tunisia", "format": "json", "limit": 1},
                         headers={"User-Agent": "ZeroMinuteDispatch/1.0"}, timeout=4)
        res = r.json()
        if res: return float(res[0]["lat"]), float(res[0]["lon"])
    except Exception: pass
    return None, None

def get_tomtom_route_points(origin_lat, origin_lon, dest_lat, dest_lon):
    key = os.getenv("TOMTOM_API_KEY")
    url = f"https://api.tomtom.com/routing/1/calculateRoute/{origin_lat},{origin_lon}:{dest_lat},{dest_lon}/json"
    try:
        r = requests.get(url, params={"key": key, "traffic": "true", "travelMode": "car"}, timeout=10)
        pts = r.json()["routes"][0]["legs"][0]["points"]
        return [[p["latitude"], p["longitude"]] for p in pts]
    except Exception:
        return [[origin_lat, origin_lon], [dest_lat, dest_lon]]

def build_ticker():
    if not st.session_state.incidents:
        return ("■ ZERO-MINUTE DISPATCH ONLINE &nbsp;&nbsp;&nbsp; "
                "■ CIVIL PROTECTION OPS ACTIVE &nbsp;&nbsp;&nbsp; "
                "■ AI PIPELINE READY &nbsp;&nbsp;&nbsp; "
                "■ AWAITING INCIDENTS &nbsp;&nbsp;&nbsp;") * 2
    items = ""
    for inc in st.session_state.incidents[-6:]:
        if inc["is_scam"]:
            items += f'<span>⚠ SCAM — {inc["location"]} — {inc["time"]}</span><span class="sep">■</span>'
        else:
            items += (f'<span>🚨 {inc["priority"]} — {inc["condition"][:35]} — '
                      f'{inc["location"]} — {inc["time"]}</span><span class="sep">■</span>')
    return items * 2


# ── Left panel (incident log) ──────────────────────────────────────────────────
def _inc_color(inc):
    if inc["is_scam"]: return "#f39c12", "#2d2000", "SCAM"
    p = inc["priority"]
    if p == "CODE_RED":    return "#e74c3c", "#1a0000", "CODE RED"
    if p == "CODE_ORANGE": return "#f39c12", "#1a0e00", "CODE ORANGE"
    return "#27ae60", "#001a00", "CODE GREEN"

def build_left_panel():
    cards_html   = ""
    details_html = ""
    incidents    = st.session_state.incidents

    if not incidents:
        cards_html = '<div style="padding:40px 16px;text-align:center;color:#222;font-size:10px;letter-spacing:2px;font-family:monospace;">NO INCIDENTS<br>SYSTEM MONITORING...</div>'
    else:
        for i, inc in enumerate(incidents):
            col, bg, badge = _inc_color(inc)
            title          = "FALSE CALL DETECTED" if inc["is_scam"] else inc["condition"][:42]
            hosp_chip      = '' if inc['is_scam'] else ('<div style="font-size:8px;color:#333;margin-top:3px;">🏥 ' + inc.get('hospital','N/A')[:28] + '</div>')
            cards_html += f"""
            <div class="inc-card" onclick="openDetail({i})" style="border-left:3px solid {col};background:{bg};">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px;">
                    <div style="font-size:10px;font-weight:600;color:#ccc;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:160px;">{title}</div>
                    <span style="font-size:7px;font-weight:700;padding:2px 5px;background:{bg};color:{col};border:1px solid {col};margin-left:6px;white-space:nowrap;letter-spacing:1px;">{badge}</span>
                </div>
                <div style="font-size:9px;color:#444;display:flex;gap:8px;flex-wrap:wrap;">
                    <span>{inc["time"]}</span>
                    <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">📍 {inc.get("location","?")[:24]}</span>
                </div>
                {hosp_chip}
            </div>"""
            hosp_row = "" if inc["is_scam"] else f"""
            <div class="dr"><span class="dl">HOSPITAL</span><span class="dv">{inc.get("hospital","N/A")}</span></div>
            <div class="dr"><span class="dl">VICTIMS</span><span class="dv" style="color:{col};">{inc.get("victims",0)}</span></div>"""
            details_html += f"""
            <div id="det-{i}" style="display:none;padding:16px;">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                    <span style="font-size:8px;font-weight:700;padding:3px 7px;background:{bg};color:{col};border:1px solid {col};letter-spacing:1px;">{badge}</span>
                    <span style="font-size:9px;color:#555;">{inc["time"]}</span>
                </div>
                <div style="font-size:11px;color:#ddd;font-weight:600;margin-bottom:10px;line-height:1.4;">
                    {"⚠ FALSE CALL DETECTED" if inc["is_scam"] else inc["condition"]}
                </div>
                <div class="dr"><span class="dl">LOCATION</span><span class="dv">{inc.get("location","Unknown")}</span></div>
                <div class="dr"><span class="dl">PRIORITY</span><span class="dv" style="color:{col};">{inc["priority"]}</span></div>
                {hosp_row}
            </div>"""

    return f"""<!DOCTYPE html>
<html><head><style>
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{height:100%;background:#080808;color:#e0e0e0;font-family:'Share Tech Mono',monospace;overflow:hidden;}}
.panel{{display:flex;flex-direction:column;height:100%;}}
.phdr{{height:28px;background:#060606;border-bottom:1px solid #111;display:flex;align-items:center;padding:0 12px;font-size:8px;font-weight:700;color:#c0392b;letter-spacing:3px;flex-shrink:0;}}
.list{{flex:1;overflow-y:auto;}}
.list::-webkit-scrollbar{{width:3px;}}
.list::-webkit-scrollbar-thumb{{background:#3a0000;}}
.inc-card{{padding:9px 12px;border-bottom:1px solid #0f0f0f;cursor:pointer;transition:background .12s;}}
.inc-card:hover{{background:rgba(255,255,255,0.02)!important;}}
.drawer{{position:fixed;top:0;right:-280px;width:280px;height:100%;background:#0a0a0a;border-left:1px solid #1e1e1e;transition:right .2s ease;z-index:100;display:flex;flex-direction:column;}}
.drawer.open{{right:0;}}
.drawer-hdr{{height:40px;display:flex;align-items:center;justify-content:space-between;padding:0 12px;border-bottom:1px solid #111;flex-shrink:0;}}
.drawer-title{{font-size:8px;color:#c0392b;letter-spacing:3px;font-weight:700;}}
.close-btn{{background:none;border:1px solid #333;color:#666;cursor:pointer;padding:3px 8px;font-size:10px;font-family:monospace;transition:all .1s;}}
.close-btn:hover{{border-color:#c0392b;color:#c0392b;}}
.dr{{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #0d0d0d;}}
.dl{{font-size:8px;color:#444;letter-spacing:1px;}}
.dv{{font-size:9px;color:#bbb;font-weight:600;text-align:right;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}}
</style></head>
<body>
<div class="panel">
    <div class="phdr">■ INCIDENT LOG — REAL-TIME</div>
    <div class="list">{cards_html}</div>
</div>
<div class="drawer" id="drawer">
    <div class="drawer-hdr">
        <span class="drawer-title">■ INCIDENT DETAIL</span>
        <button class="close-btn" onclick="closeDetail()">✕ CLOSE</button>
    </div>
    <div style="flex:1;overflow-y:auto;">{details_html}</div>
</div>
<script>
function openDetail(idx){{
    document.querySelectorAll('[id^="det-"]').forEach(d=>d.style.display='none');
    var el=document.getElementById('det-'+idx);
    if(el)el.style.display='block';
    document.getElementById('drawer').classList.add('open');
}}
function closeDetail(){{document.getElementById('drawer').classList.remove('open');}}
</script>
</body></html>"""


# ── Right panel (hospital resources) ──────────────────────────────────────────
def build_right_panel():
    cards = ""
    for hname, res in st.session_state.hospital_resources.items():
        short = hname.replace("Hôpital ", "").replace("Clinique ", "")
        status = res["status"]
        sc    = "#27ae60" if status == "OPERATIONAL" else ("#f39c12" if status == "STRAINED" else "#e74c3c")
        sc_bg = "#001a00" if status == "OPERATIONAL" else ("#1a0e00" if status == "STRAINED" else "#1a0000")

        def bar(val, mx):
            c   = get_resource_class(val, mx)
            pct = int(100 * val / mx) if mx > 0 else 0
            return (f'<div style="background:#111;height:5px;border-radius:1px;overflow:hidden;margin-top:3px;">'
                    f'<div style="width:{pct}%;height:100%;background:{c};transition:width .3s;"></div></div>')

        bc  = get_resource_class(res["trauma_bays"], res.get("trauma_bays_max", 4))
        ac  = get_resource_class(res["ambulances"],  res.get("ambulances_max",  8))
        sgc = get_resource_class(res["surgeons"],    res.get("surgeons_max",    5))
        cards += f"""
        <div style="padding:10px 12px;border-bottom:1px solid #0e0e0e;cursor:pointer;transition:background .12s;"
             onmouseover="this.style.background='#0d0d0d'" onmouseout="this.style.background='transparent'">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <div style="font-size:10px;font-weight:700;color:#ccc;">{short}</div>
                <span style="font-size:7px;font-weight:700;padding:2px 5px;background:{sc_bg};color:{sc};border:1px solid {sc};letter-spacing:1px;">{status}</span>
            </div>
            <div style="font-size:8px;color:#444;margin-bottom:3px;display:flex;justify-content:space-between;"><span>TRAUMA BAYS</span><span style="color:{bc};">{res["trauma_bays"]}</span></div>
            {bar(res["trauma_bays"], res.get("trauma_bays_max", 4))}
            <div style="font-size:8px;color:#444;margin-top:5px;margin-bottom:3px;display:flex;justify-content:space-between;"><span>AMBULANCES</span><span style="color:{ac};">{res["ambulances"]}</span></div>
            {bar(res["ambulances"], res.get("ambulances_max", 8))}
            <div style="font-size:8px;color:#444;margin-top:5px;margin-bottom:3px;display:flex;justify-content:space-between;"><span>SURGEONS ON CALL</span><span style="color:{sgc};">{res["surgeons"]}</span></div>
            {bar(res["surgeons"], res.get("surgeons_max", 5))}
        </div>"""

    stats = f"""
    <div style="padding:10px 12px;">
        <div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #0e0e0e;font-size:9px;"><span style="color:#444;letter-spacing:1px;">TOTAL INCIDENTS</span><span style="color:#bbb;font-weight:700;">{st.session_state.total_today}</span></div>
        <div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #0e0e0e;font-size:9px;"><span style="color:#444;letter-spacing:1px;">ACTIVE CODE RED</span><span style="color:#e74c3c;font-weight:700;">{st.session_state.active_incidents}</span></div>
        <div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #0e0e0e;font-size:9px;"><span style="color:#444;letter-spacing:1px;">SCAMS DETECTED</span><span style="color:#f39c12;font-weight:700;">{st.session_state.scams_detected}</span></div>
        <div style="display:flex;justify-content:space-between;padding:5px 0;font-size:9px;"><span style="color:#444;letter-spacing:1px;">SYSTEM STATUS</span><span style="color:#27ae60;font-weight:700;">OPERATIONAL</span></div>
    </div>"""

    return f"""<!DOCTYPE html>
<html><head><style>
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{height:100%;background:#080808;color:#e0e0e0;font-family:'Share Tech Mono',monospace;overflow:hidden;}}
.panel{{display:flex;flex-direction:column;height:100%;}}
.phdr{{height:28px;background:#060606;border-bottom:1px solid #111;display:flex;align-items:center;padding:0 12px;font-size:8px;font-weight:700;color:#c0392b;letter-spacing:3px;flex-shrink:0;}}
.scroll{{flex:1;overflow-y:auto;}}
.scroll::-webkit-scrollbar{{width:3px;}}
.scroll::-webkit-scrollbar-thumb{{background:#3a0000;}}
.shdr{{height:24px;background:#060606;border-top:1px solid #111;border-bottom:1px solid #111;display:flex;align-items:center;padding:0 12px;font-size:7px;font-weight:700;color:#555;letter-spacing:3px;flex-shrink:0;}}
</style></head>
<body>
<div class="panel">
    <div class="phdr">■ HOSPITAL RESOURCES</div>
    <div class="scroll">
        {cards}
        <div class="shdr">SESSION STATISTICS</div>
        {stats}
    </div>
</div>
</body></html>"""


# ── Triage modal ───────────────────────────────────────────────────────────────
def build_triage_modal(data, loc_input):
    if not data: return ""
    is_scam  = data["scam_assessment"]["is_suspected_scam"]
    priority = data["incident_metadata"]["priority_level"]
    meta     = data["incident_metadata"]
    med      = data["extracted_medical_entities"]
    scam     = data["scam_assessment"]
    hosp     = data.get("hospital_alert") or {}
    traffic  = hosp.get("traffic_route") or {}
    disp     = data.get("dispatch_recommendation") or {}
    hazards  = data.get("environmental_hazards") or []
    pq       = data.get("priority_queue") or {}
    verify   = data.get("requires_human_verification", False)

    if is_scam:
        pcol, pbg, plabel = "#f39c12", "#1a1400", "⚠ SCAM CALL DETECTED"
    elif priority == "CODE_RED":
        pcol, pbg, plabel = "#e74c3c", "#1a0000", "🔴 CODE RED — CRITICAL EMERGENCY"
    elif priority == "CODE_ORANGE":
        pcol, pbg, plabel = "#f39c12", "#1a0e00", "🟠 CODE ORANGE — URGENT"
    else:
        pcol, pbg, plabel = "#27ae60", "#001a00", "🟢 CODE GREEN — NON-CRITICAL"

    loc = loc_input or meta.get("location_description") or "Unknown"

    def tab_onclick(tid):
        ids = "['zmd-t1','zmd-t2','zmd-t3','zmd-t4','zmd-t5']"
        return (
            f"{ids}.forEach(function(id){{document.getElementById(id).style.display='none';}});"
            f"document.querySelectorAll('.zmd-tab').forEach(function(b){{b.style.borderBottomColor='transparent';b.style.color='#444';}});"
            f"document.getElementById('{tid}').style.display='block';"
            f"this.style.borderBottomColor='{pcol}';this.style.color='{pcol}';"
        )

    # Tab 1 — Patient
    if is_scam:
        tab1_body = f"""<div style="padding:20px;">
            <div style="background:#1a1400;border:1px solid #f39c12;padding:16px;text-align:center;margin-bottom:16px;">
                <div style="font-size:20px;font-weight:900;color:#f39c12;letter-spacing:3px;">FALSE CALL — DO NOT DISPATCH</div>
            </div>
            <div class="zdr"><span class="zdl">FINAL SCAM PROBABILITY</span><span class="zdv" style="color:#f39c12;">{int(scam['final_scam_probability']*100)}%</span></div>
            <div class="zdr"><span class="zdl">GEMINI SCORE</span><span class="zdv" style="color:#f39c12;">{int(scam['gemini_scam_score']*100)}%</span></div>
            <div class="zdr"><span class="zdl">NLP SCORE</span><span class="zdv">{int(scam['nlp_scam_score']*100)}%</span></div>
            <div class="zdr"><span class="zdl">ACTION REQUIRED</span><span class="zdv" style="color:#e74c3c;">TRACE &amp; LOG</span></div>
        </div>"""
    else:
        haz_tags = "".join(f'<span style="display:inline-block;font-size:8px;font-weight:700;padding:2px 6px;background:#1a0000;color:#e74c3c;border:1px solid #c0392b;margin-right:4px;margin-bottom:4px;">⚠ {h}</span>' for h in hazards) or '<span style="color:#333;font-size:9px;">None detected</span>'
        tab1_body = f"""<div style="padding:16px;">
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:14px;">
                <div class="zmcard"><div class="zmv" style="color:#e74c3c;">{meta['estimated_victims']}</div><div class="zml">Victims</div></div>
                <div class="zmcard"><div class="zmv" style="color:#27ae60;">{int(meta['confidence_score']*100)}%</div><div class="zml">AI Confidence</div></div>
                <div class="zmcard"><div class="zmv" style="color:#3498db;font-size:12px;">{loc[:16]}</div><div class="zml">Location</div></div>
            </div>
            <div class="zshdr">PATIENT VITALS</div>
            <div class="zdr"><span class="zdl">PRIMARY CONDITION</span><span class="zdv" style="color:#e74c3c;">{med['suspected_primary_condition']}</span></div>
            <div class="zdr"><span class="zdl">CONSCIOUSNESS</span><span class="zdv" style="color:#f39c12;">{med['consciousness_level']}</span></div>
            <div class="zdr"><span class="zdl">RESPIRATORY</span><span class="zdv" style="color:#3498db;">{med['respiratory_estimate']}</span></div>
            <div class="zshdr" style="margin-top:10px;">ENVIRONMENTAL HAZARDS</div>
            <div style="padding:8px 0;">{haz_tags}</div>
            {"" if not verify else '<div style="margin-top:10px;background:#1a0000;border:1px solid #c0392b;padding:8px 12px;font-size:9px;color:#e74c3c;font-weight:700;letter-spacing:2px;text-align:center;">⚠ HUMAN VERIFICATION REQUIRED</div>'}
        </div>"""

    # Tab 2 — Hospital
    surgeons_html = "".join(f'<div style="font-size:9px;color:#aaa;padding:3px 0;">▶ {s}</div>' for s in hosp.get("surgeons_on_call", [])) or '<span style="color:#333;font-size:9px;">N/A</span>'
    equip_html    = "".join(f'<span style="display:inline-block;font-size:8px;font-weight:700;padding:2px 6px;background:#001a00;color:#27ae60;border:1px solid #1e8449;margin-right:4px;margin-bottom:4px;">✓ {e}</span>' for e in hosp.get("equipment", []))
    prep_block    = '' if not hosp.get('preparation_instructions') else ('<div style="background:#001a0a;border-left:3px solid #27ae60;padding:8px 12px;font-size:9px;color:#aaa;line-height:1.6;margin-bottom:10px;"><div style="font-size:7px;color:#27ae60;letter-spacing:2px;font-weight:700;margin-bottom:4px;">▶ PREPARATION INSTRUCTIONS</div>' + hosp['preparation_instructions'] + '</div>')
    traf_block    = '' if not traffic.get('traffic_condition') else ('<div style="background:#00081a;border-left:3px solid #3498db;padding:8px 12px;font-size:9px;color:#aaa;"><div style="font-size:7px;color:#3498db;letter-spacing:2px;font-weight:700;margin-bottom:4px;">▶ TRAFFIC STATUS</div>' + traffic['traffic_condition'] + ' — ' + str(traffic.get('travel_time_minutes', 0)) + ' min travel time</div>')
    equip_block   = '' if not equip_html else ('<div class="zshdr" style="margin-top:10px;">AVAILABLE EQUIPMENT</div><div style="padding:8px 0;">' + equip_html + '</div>')
    tab2_body = f"""<div style="padding:16px;">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px;">
            <div>
                <div class="zshdr">RECEIVING FACILITY</div>
                <div class="zdr"><span class="zdl">NAME</span><span class="zdv">{hosp.get("name","N/A")}</span></div>
                <div class="zdr"><span class="zdl">CITY</span><span class="zdv">{hosp.get("city","N/A")}</span></div>
                <div class="zdr"><span class="zdl">DISTANCE</span><span class="zdv">{hosp.get("distance_km","—")} km</span></div>
                <div class="zdr"><span class="zdl">ETA</span><span class="zdv" style="color:#e74c3c;">{hosp.get("eta_minutes","—")} min</span></div>
                <div class="zdr"><span class="zdl">AVAILABLE BAYS</span><span class="zdv" style="color:#27ae60;">{hosp.get("available_bays","—")}</span></div>
            </div>
            <div><div class="zshdr">SURGEONS ON CALL</div><div style="padding:6px 0;">{surgeons_html}</div></div>
        </div>
        {prep_block}{traf_block}{equip_block}
    </div>"""

    # Tab 3 — Dispatch
    spec_tags = "".join(f'<span style="display:inline-block;font-size:8px;font-weight:700;padding:2px 6px;background:#00081a;color:#3498db;border:1px solid #2980b9;margin-right:4px;margin-bottom:4px;">▶ {s}</span>' for s in disp.get("required_specialists", [])) or '<span style="color:#333;font-size:9px;">N/A</span>'
    equip_d   = "".join(f'<span style="display:inline-block;font-size:8px;font-weight:700;padding:2px 6px;background:#001a00;color:#27ae60;border:1px solid #1e8449;margin-right:4px;margin-bottom:4px;">✓ {e}</span>' for e in disp.get("equipment_loadout", [])) or '<span style="color:#333;font-size:9px;">Standard kit</span>'
    tab3_body = f"""<div style="padding:16px;">
        <div class="zshdr">REQUIRED SPECIALISTS</div><div style="padding:8px 0;">{spec_tags}</div>
        <div class="zshdr" style="margin-top:8px;">EQUIPMENT LOADOUT</div><div style="padding:8px 0;">{equip_d}</div>
        <div class="zshdr" style="margin-top:8px;">PRIORITY QUEUE</div>
        <div class="zdr"><span class="zdl">QUEUE POSITION</span><span class="zdv" style="color:#e74c3c;">#{pq.get("queue_position",1)} / {pq.get("total_active_incidents",1)}</span></div>
        <div class="zdr"><span class="zdl">AMBULANCES AVAILABLE</span><span class="zdv" style="color:#27ae60;">{pq.get("ambulances_available",3)}</span></div>
        <div class="zdr"><span class="zdl">REASON</span><span class="zdv">{str(pq.get("priority_reason","—"))[:30]}</span></div>
    </div>"""

    # Tab 4 — Scam
    ind_html = "".join(f'<div style="font-size:9px;color:#f39c12;padding:3px 0;border-bottom:1px solid #111;">⚠ {ind}</div>' for ind in scam.get("scam_indicators", [])) or '<span style="color:#333;font-size:9px;">No indicators detected</span>'
    def sbar(val):
        pct = int(val * 100)
        c = "#27ae60" if pct < 30 else ("#f39c12" if pct < 70 else "#e74c3c")
        return f'<div style="background:#111;height:6px;border-radius:2px;overflow:hidden;margin-top:3px;"><div style="width:{pct}%;height:100%;background:{c};"></div></div>'
    tab4_body = f"""<div style="padding:16px;">
        <div class="zdr"><span class="zdl">VERDICT</span><span class="zdv" style="color:{'#e74c3c' if scam['is_suspected_scam'] else '#27ae60'};"> {"⚠ SUSPECTED SCAM" if scam['is_suspected_scam'] else "✓ GENUINE CALL"}</span></div>
        <div style="margin:10px 0;"><div style="font-size:8px;color:#444;letter-spacing:1px;display:flex;justify-content:space-between;"><span>GEMINI SCORE</span><span style="color:#bbb;">{int(scam['gemini_scam_score']*100)}%</span></div>{sbar(scam['gemini_scam_score'])}</div>
        <div style="margin:10px 0;"><div style="font-size:8px;color:#444;letter-spacing:1px;display:flex;justify-content:space-between;"><span>NLP (BART) SCORE</span><span style="color:#bbb;">{int(scam['nlp_scam_score']*100)}%</span></div>{sbar(scam['nlp_scam_score'])}</div>
        <div style="margin:10px 0;"><div style="font-size:8px;color:#c0392b;letter-spacing:1px;font-weight:700;display:flex;justify-content:space-between;"><span>FINAL PROBABILITY</span><span>{int(scam['final_scam_probability']*100)}%</span></div>{sbar(scam['final_scam_probability'])}</div>
        <div class="zshdr" style="margin-top:10px;">SCAM INDICATORS</div>
        <div style="padding:6px 0;">{ind_html}</div>
    </div>"""

    # Tab 5 — Raw JSON
    raw = json.dumps(data, indent=2)
    tab5_body = f'<div style="padding:12px;"><pre style="background:#040404;border:1px solid #111;padding:12px;font-size:8px;color:#2ecc71;font-family:monospace;overflow:auto;max-height:340px;line-height:1.5;">{raw}</pre></div>'

    return f"""
<style>
#zmd-overlay{{position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.88);z-index:200;display:flex;align-items:center;justify-content:center;font-family:'Share Tech Mono',monospace;}}
.zmd-modal{{background:#080808;border:1px solid #1e1e1e;border-top:3px solid {pcol};width:min(860px,94vw);height:min(600px,90vh);display:flex;flex-direction:column;overflow:hidden;box-shadow:0 0 60px rgba(0,0,0,0.95);}}
.zmd-top{{background:{pbg};border-bottom:1px solid #1a1a1a;padding:12px 16px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0;}}
.zmd-title{{font-size:13px;font-weight:900;color:{pcol};letter-spacing:3px;}}
.zmd-close{{background:none;border:1px solid #333;color:#555;cursor:pointer;padding:4px 12px;font-size:11px;font-family:monospace;letter-spacing:1px;}}
.zmd-close:hover{{border-color:{pcol};color:{pcol};}}
.zmd-tabs{{display:flex;border-bottom:1px solid #111;background:#050505;flex-shrink:0;}}
.zmd-tab{{flex:1;padding:9px 4px;background:none;border:none;color:#444;font-family:monospace;font-size:8px;letter-spacing:1px;cursor:pointer;text-transform:uppercase;border-bottom:2px solid transparent;}}
.zmd-body{{flex:1;overflow-y:auto;}}
.zmd-body::-webkit-scrollbar{{width:3px;}}
.zmd-body::-webkit-scrollbar-thumb{{background:#2a0000;}}
.zdr{{display:flex;justify-content:space-between;align-items:flex-start;padding:6px 0;border-bottom:1px solid #0d0d0d;}}
.zdl{{font-size:8px;color:#444;letter-spacing:1px;white-space:nowrap;}}
.zdv{{font-size:9px;color:#bbb;font-weight:600;text-align:right;max-width:55%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}}
.zshdr{{font-size:7px;color:#555;letter-spacing:2px;font-weight:700;text-transform:uppercase;padding:5px 0;border-bottom:1px solid #111;margin-bottom:2px;}}
.zmcard{{background:#0a0a0a;border:1px solid #111;padding:10px;text-align:center;}}
.zmv{{font-size:22px;font-weight:800;line-height:1;}}
.zml{{font-size:7px;color:#444;letter-spacing:2px;text-transform:uppercase;margin-top:4px;}}
</style>
<div id="zmd-overlay">
  <div class="zmd-modal">
    <div class="zmd-top">
        <div class="zmd-title">{plabel}</div>
        <button class="zmd-close" onclick="document.getElementById('zmd-overlay').style.display='none'">✕ CLOSE</button>
    </div>
    <div class="zmd-tabs">
        <button class="zmd-tab" style="color:{pcol};border-bottom-color:{pcol};" onclick="{tab_onclick('zmd-t1')}">PATIENT</button>
        <button class="zmd-tab" onclick="{tab_onclick('zmd-t2')}">HOSPITAL</button>
        <button class="zmd-tab" onclick="{tab_onclick('zmd-t3')}">DISPATCH</button>
        <button class="zmd-tab" onclick="{tab_onclick('zmd-t4')}">SCAM ANALYSIS</button>
        <button class="zmd-tab" onclick="{tab_onclick('zmd-t5')}">RAW JSON</button>
    </div>
    <div class="zmd-body">
        <div id="zmd-t1" style="display:block;">{tab1_body}</div>
        <div id="zmd-t2" style="display:none;">{tab2_body}</div>
        <div id="zmd-t3" style="display:none;">{tab3_body}</div>
        <div id="zmd-t4" style="display:none;">{tab4_body}</div>
        <div id="zmd-t5" style="display:none;">{tab5_body}</div>
    </div>
  </div>
</div>"""


# ══════════════════════════════════════════════════════════════════════════════
# RENDER
# ══════════════════════════════════════════════════════════════════════════════
amb_deployed = len(st.session_state.ambulances)

# ── Navbar ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="ops-navbar">
    <div class="logo-wrap">
        <img class="logo-img" src="{TUNISIA_LOGO}" alt="Tunisia" onerror="this.style.display='none'">
        <img class="logo-img" src="{CIVIL_LOGO}"   alt="Civil Protection" onerror="this.style.display='none'">
        <div class="brand">
            <div class="brand-name">Zero-Minute Dispatch</div>
            <div class="brand-sub">CIVIL PROTECTION COMMAND CENTER — AI TRIAGE SYSTEM</div>
        </div>
    </div>
    <div class="stat-row">
        <div class="stat-box"><div class="stat-num s-red">{st.session_state.active_incidents}</div><div class="stat-lbl">Active</div></div>
        <div class="stat-box"><div class="stat-num s-white">{st.session_state.total_today}</div><div class="stat-lbl">Today</div></div>
        <div class="stat-box"><div class="stat-num s-gold">{st.session_state.scams_detected}</div><div class="stat-lbl">Scams</div></div>
        <div class="stat-box"><div class="stat-num s-blue">{amb_deployed}</div><div class="stat-lbl">Deployed</div></div>
    </div>
    <div class="live-badge"><div class="live-dot"></div><div class="live-text">LIVE</div></div>
</div>
""", unsafe_allow_html=True)

# ── Ticker ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="ticker-wrap">
    <div class="ticker-inner">{build_ticker()}</div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# THREE-COLUMN LAYOUT
# ══════════════════════════════════════════════════════════════════════════════
col_left, col_mid, col_right = st.columns([1, 3, 1], gap="small")

with col_left:
    components.html(build_left_panel(), height=2000, scrolling=False)


# ── CENTER: Map + Upload ───────────────────────────────────────────────────────
with col_mid:

    # ── Map header + sim controls ─────────────────────────────────────────────
    st.markdown('<div class="panel-hdr">■ DISPATCH MAP — LIVE OPERATIONS</div>', unsafe_allow_html=True)

    active_ambs = [a for a in st.session_state.ambulances if a["status"] != "ARRIVED"]
    map_ctl1, map_ctl2 = st.columns([5, 1], gap="small")
    with map_ctl2:
        sim_clicked = st.button("▶ SIM", use_container_width=True,
                                disabled=not active_ambs, key="sim_btn")
    with map_ctl1:
        if st.session_state.ambulances:
            parts = []
            for a in st.session_state.ambulances:
                pct = int(100 * a["step"] / a["total_steps"]) if a["total_steps"] > 0 else 100
                parts.append(f'<span style="color:{a["color"]};font-family:monospace;font-size:9px;">{a["id"]} {a["status"]} {pct}%</span>')
            st.markdown('<span style="color:#222"> | </span>'.join(parts), unsafe_allow_html=True)

    if sim_clicked:
        for a in st.session_state.ambulances:
            if a["status"] == "ARRIVED": continue
            advance = max(1, int(a["total_steps"] * 0.08))
            a["step"] = min(a["step"] + advance, a["total_steps"])
            mid = a.get("mid_idx", a["total_steps"] // 2)
            if a["step"] >= a["total_steps"]: a["status"] = "ARRIVED"
            elif a["step"] > mid:             a["status"] = "TO_HOSPITAL"
            elif a["step"] >= mid:            a["status"] = "AT_SCENE"
            else:                             a["status"] = "EN_ROUTE"
        st.rerun()


    # ── Build Folium map ──────────────────────────────────────────────────────

    m = folium.Map(
        location=[36.8190, 10.1660],
        zoom_start=11,
        tiles='cartodbdark_matter',
        attr='CartoDB'
    )

    # HQ marker
    folium.CircleMarker(
        location=[HQ_LAT, HQ_LON],
        radius=10,
        color='#c0392b',
        fill=True,
        fill_color='#c0392b',
        fill_opacity=0.8,
        tooltip='Civil Protection HQ'
    ).add_to(m)

    # Hospital markers
    for h_name, h_coords in HOSPITAL_COORDS.items():
        folium.CircleMarker(
            location=[h_coords['lat'], h_coords['lon']],
            radius=7,
            color='#3498db',
            fill=True,
            fill_color='#3498db',
            fill_opacity=0.7,
            tooltip=h_name
        ).add_to(m)

    # Incident markers
    for inc_m in st.session_state.incident_markers:
        badge_col = '#e74c3c' if inc_m['priority'] == 'CODE_RED' else '#f39c12'
        folium.CircleMarker(
            location=[inc_m['lat'], inc_m['lon']],
            radius=12,
            color=badge_col,
            fill=True,
            fill_color=badge_col,
            fill_opacity=0.4,
            tooltip=f"{inc_m['id']} — {inc_m['condition'][:30]}"
        ).add_to(m)

    # Ambulance routes and markers
    for a in st.session_state.ambulances:
        route_pts = a.get('route_points', [])
        if not route_pts:
            continue
        folium.PolyLine(
            locations=route_pts,
            color=a['color'],
            weight=3,
            opacity=0.8,
            dash_array='8'
        ).add_to(m)
        pos = route_pts[min(a['step'], len(route_pts)-1)]
        folium.CircleMarker(
            location=pos,
            radius=8,
            color=a['color'],
            fill=True,
            fill_color=a['color'],
            fill_opacity=0.9,
            tooltip=f"{a['id']} — {a['status']}"
        ).add_to(m)

    st_folium(m, height=280, width=700, returned_objects=[])
    # ── Input section ─────────────────────────────────────────────────────────
    st.markdown('<div style="height:1px;background:#1a1a1a;margin:4px 0;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="panel-hdr">■ INCIDENT INPUT — SCENE RECORDING</div>', unsafe_allow_html=True)

    up_col1, up_col2 = st.columns([3, 2], gap="small")
    with up_col1:
        uploaded_file = st.file_uploader(
            "Scene Recording", type=["mp4", "mp3", "wav", "m4a", "ogg", "webm", "mpeg4"],
            label_visibility="visible"
        )
    with up_col2:
        location_input = st.text_input("Incident Location", placeholder="Route Nationale 9, Tunis")

    btn_col1, btn_col2 = st.columns([3, 1], gap="small")
    with btn_col1:
        analyze_btn = st.button("■  ANALYZE EMERGENCY SCENE  ■", type="primary", use_container_width=True)
    with btn_col2:
        if st.session_state.last_report:
            report_label = "✕ CLOSE" if st.session_state.show_modal else "■ REPORT ■"
            if st.button(report_label, use_container_width=True, key="view_report_btn"):
                st.session_state.show_modal = not st.session_state.show_modal
                st.rerun()

    stream_placeholder = st.empty()

    # ── Streaming analysis ────────────────────────────────────────────────────
    if uploaded_file and analyze_btn:
        files     = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        form_data = {"location": location_input} if location_input else {}
        data      = None

        with st.spinner("🛰 AI pipeline initializing..."):
            try:
                with requests.post(
                    f"{API_URL}/analyze/stream",
                    files=files, data=form_data or None,
                    stream=True, timeout=300
                ) as resp:
                    raw_output = ""
                    for line in resp.iter_lines():
                        if not line: continue
                        decoded = line.decode("utf-8")
                        if not decoded.startswith("data: "): continue
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
                                f'<div class="stream-box">'
                                f'<div class="stream-label">■ AI GENERATING TRIAGE REPORT...</div>'
                                f'{raw_output[-450:]}</div>',
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

        is_scam       = data["scam_assessment"]["is_suspected_scam"]
        priority      = data["incident_metadata"]["priority_level"]
        condition     = data["extracted_medical_entities"]["suspected_primary_condition"] or "Unknown"
        hospital_name = (data.get("hospital_alert") or {}).get("name", "N/A")

        st.session_state.incidents.insert(0, {
            "time":      datetime.now().strftime("%H:%M:%S"),
            "priority":  priority,
            "condition": condition,
            "location":  location_input or data["incident_metadata"]["location_description"] or "Unknown",
            "victims":   data["incident_metadata"]["estimated_victims"],
            "hospital":  hospital_name,
            "is_scam":   is_scam,
        })

        if is_scam:
            st.session_state.scams_detected += 1
        else:
            st.session_state.total_today += 1
            if priority == "CODE_RED":
                st.session_state.active_incidents += 1
            for hosp_name, resources in st.session_state.hospital_resources.items():
                if hosp_name in hospital_name or hospital_name in hosp_name:
                    if resources["trauma_bays"] > 0: resources["trauma_bays"] -= 1
                    if resources["ambulances"]  > 0: resources["ambulances"]  -= 1
                    if resources["surgeons"]    > 0: resources["surgeons"]    -= 1
                    if resources["trauma_bays"] <= 1: resources["status"] = "CRITICAL"
                    elif resources["trauma_bays"] <= 2: resources["status"] = "STRAINED"

        if not is_scam and priority in ("CODE_RED", "CODE_ORANGE"):
            inc_lat, inc_lon = dashboard_geocode(location_input)
            if not inc_lat:
                offset   = len(st.session_state.incident_markers) * 0.006
                inc_lat  = 36.8065 + offset
                inc_lon  = 10.1815 + offset * 0.5

            h_coords     = HOSPITAL_COORDS.get(hospital_name, {"lat": 36.8065, "lon": 10.1815})
            inc_id       = f"INC-{len(st.session_state.incident_markers)+1:03d}"
            st.session_state.incident_markers.append({
                "id": inc_id, "lat": inc_lat, "lon": inc_lon,
                "priority": priority, "condition": condition,
                "victims": data["incident_metadata"]["estimated_victims"],
                "time": datetime.now().strftime("%H:%M:%S"),
            })

            st.session_state.amb_counter += 1
            amb_id       = f"AMB-{st.session_state.amb_counter:03d}"
            h_lat, h_lon = h_coords["lat"], h_coords["lon"]
            leg1         = get_tomtom_route_points(HQ_LAT, HQ_LON, inc_lat, inc_lon)
            leg2         = get_tomtom_route_points(inc_lat, inc_lon, h_lat, h_lon)
            route_points = leg1 + leg2[1:]
            mid_idx      = len(leg1) - 1

            st.session_state.ambulances.append({
                "id": amb_id, "color": next_amb_color(),
                "hospital_name": hospital_name,
                "route_points": route_points, "mid_idx": mid_idx,
                "step": 0, "total_steps": len(route_points) - 1,
                "status": "EN_ROUTE", "incident_id": inc_id,
                "condition": condition[:40],
            })

        st.session_state.show_notification = True
        st.session_state.show_modal        = True
        st.rerun()


with col_right:
    components.html(build_right_panel(), height=2000, scrolling=False)


# ══════════════════════════════════════════════════════════════════════════════
# TRIAGE MODAL
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.show_modal and st.session_state.last_report:
    loc_val = ""
    try:
        loc_val = location_input
    except NameError:
        pass
    st.markdown(build_triage_modal(st.session_state.last_report, loc_val), unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.show_notification and st.session_state.incidents:
    last = st.session_state.incidents[0]
    if last["is_scam"]:
        notif_html = f"""
        <div class="notif-stack">
        <div class="notif-card scam">
            <div class="notif-lbl scam">⚠ SCAM DETECTED</div>
            <div class="notif-title">FALSE CALL — DO NOT DISPATCH</div>
            <div class="notif-sub">📍 {last['location']} — {last['time']}</div>
        </div></div>"""
    else:
        notif_html = f"""
        <div class="notif-stack">
        <div class="notif-card">
            <div class="notif-lbl">🚨 NEW INCIDENT — {last['priority']}</div>
            <div class="notif-title">{last['condition'][:55]}</div>
            <div class="notif-sub">📍 {last['location']} — 👥 {last['victims']} victim(s) — {last['time']}</div>
        </div></div>"""
    st.markdown(notif_html, unsafe_allow_html=True)
