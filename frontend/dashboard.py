import streamlit as st
import requests

st.set_page_config(
    page_title="Zero-Minute Dispatch",
    page_icon="🚨",
    layout="wide"
)

st.markdown("""
<style>
    .code-red {
        background-color: #8B0000;
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        font-size: 2.5em;
        font-weight: bold;
    }
    .code-orange {
        background-color: #FF8C00;
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        font-size: 2.5em;
        font-weight: bold;
    }
    .code-green {
        background-color: #006400;
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        font-size: 2.5em;
        font-weight: bold;
    }
    .scam-alert {
        background-color: #FFD700;
        color: black;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        font-size: 2.5em;
        font-weight: bold;
    }
    .verification-flag {
        background-color: #FF4500;
        color: white;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("# 🚨 Zero-Minute Dispatch")
st.markdown("### AI-Powered Emergency Triage — Civil Protection Operations")
st.divider()

col1, col2 = st.columns([2, 1])
with col1:
    uploaded_file = st.file_uploader(
        "Upload Emergency Scene (Video or Audio)",
        type=["mp4", "mp3", "wav", "m4a"]
    )
with col2:
    location_input = st.text_input(
        "📍 Caller Location",
        placeholder="e.g. Route Nationale 9, Sidi Bou Said"
    )

if uploaded_file and st.button("🔍 ANALYZE EMERGENCY SCENE", type="primary", use_container_width=True):

    with st.spinner("🛰️ AI pipeline processing..."):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        try:
            response = requests.post("http://localhost:8000/analyze", files=files, timeout=120)
            data = response.json()
        except Exception as e:
            st.error(f"Pipeline error: {e}")
            st.stop()

    # SCAM DETECTION
    if data["scam_assessment"]["is_suspected_scam"]:
        st.markdown('<div class="scam-alert">⚠️ SCAM CALL DETECTED — DO NOT DISPATCH</div>', unsafe_allow_html=True)
        st.markdown("---")

        c1, c2, c3 = st.columns(3)
        with c1:
            prob = data["scam_assessment"]["final_scam_probability"] * 100
            st.metric("Scam Probability", f"{prob:.0f}%")
        with c2:
            st.metric("Caller Location", location_input or "TRACE REQUIRED")
        with c3:
            st.metric("Action", "Alert Law Enforcement")

        indicators = data["scam_assessment"]["scam_indicators"]
        if indicators:
            st.markdown("**Scam Indicators:**")
            for indicator in indicators:
                st.markdown(f"• {indicator}")
        st.stop()

    # PRIORITY BANNER
    priority = data["incident_metadata"]["priority_level"]
    if priority == "CODE_RED":
        st.markdown('<div class="code-red">🔴 CODE RED — CRITICAL EMERGENCY</div>', unsafe_allow_html=True)
    elif priority == "CODE_ORANGE":
        st.markdown('<div class="code-orange">🟠 CODE ORANGE — URGENT</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="code-green">🟢 CODE GREEN — NON CRITICAL</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ROW 1: VICTIMS + LOCATION + CONFIDENCE
    st.markdown("### 👥 Incident Overview")
    c1, c2, c3 = st.columns(3)
    with c1:
        victims = data["incident_metadata"]["estimated_victims"]
        st.metric("🚨 Victims Involved", victims)
    with c2:
        location = location_input or data["incident_metadata"]["location_description"] or "Unknown"
        st.metric("📍 Location", location)
    with c3:
        confidence = data["incident_metadata"]["confidence_score"] * 100
        st.metric("🎯 AI Confidence", f"{confidence:.0f}%")

    st.markdown("---")

    # ROW 2: PATIENT ASSESSMENT
    st.markdown("### 🩺 Patient Assessment")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Suspected Condition**")
        condition = data["extracted_medical_entities"]["suspected_primary_condition"] or "Unknown"
        st.error(condition)
    with c2:
        st.markdown("**Consciousness Level**")
        consciousness = data["extracted_medical_entities"]["consciousness_level"] or "Unknown"
        if any(word in consciousness for word in ["Unresponsive", "Unconscious"]):
            st.error(consciousness)
        else:
            st.warning(consciousness)
    with c3:
        st.markdown("**Respiratory Status**")
        respiratory = data["extracted_medical_entities"]["respiratory_estimate"] or "Unknown"
        st.warning(respiratory)

    st.markdown("---")

    # ROW 3: DISPATCH RECOMMENDATION
    st.markdown("### 🎒 Dispatch Recommendation")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Required Equipment**")
        equipment = data["dispatch_recommendation"]["equipment_loadout"]
        if equipment:
            for item in equipment:
                st.markdown(f"✅ {item}")
        else:
            st.markdown("No equipment required")
    with c2:
        st.markdown("**Required Specialists**")
        specialists = data["dispatch_recommendation"]["required_specialists"]
        if specialists:
            for specialist in specialists:
                st.markdown(f"👨‍⚕️ {specialist}")
        else:
            st.markdown("No specialists required")

    st.markdown("---")

    # ROW 4: ENVIRONMENTAL HAZARDS
    hazards = data["environmental_hazards"]
    if hazards:
        st.markdown("### ⚠️ Environmental Hazards")
        cols = st.columns(len(hazards))
        for i, hazard in enumerate(hazards):
            with cols[i]:
                st.error(f"⚠️ {hazard}")
        st.markdown("---")

    # VERIFICATION FLAG
    if data["requires_human_verification"]:
        st.markdown(
            '<div class="verification-flag">⚠️ HUMAN VERIFICATION REQUIRED</div>',
            unsafe_allow_html=True
        )

    # RAW JSON
    with st.expander("🔧 Raw AI Output"):
        st.json(data)