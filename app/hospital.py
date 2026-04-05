TUNISIA_HOSPITALS = [
    {
        "name": "Hôpital Charles Nicolle",
        "city": "Tunis",
        "lat": 36.8065,
        "lon": 10.1815,
        "specialties": ["trauma", "cardiac", "neurology", "burns"],
        "trauma_bays": 4,
        "available_bays": 2,
        "surgeons_on_call": ["Trauma Surgeon", "Neurosurgeon", "Cardiologist"],
        "equipment": ["Ventilator", "Defibrillator", "CT Scanner", "Blood Bank"]
    },
    {
        "name": "Hôpital Habib Thameur",
        "city": "Tunis",
        "lat": 36.8189,
        "lon": 10.1658,
        "specialties": ["trauma", "orthopedic", "general"],
        "trauma_bays": 3,
        "available_bays": 1,
        "surgeons_on_call": ["Trauma Surgeon", "Orthopedic Surgeon"],
        "equipment": ["Ventilator", "X-Ray", "Blood Bank"]
    },
    {
        "name": "Hôpital Militaire de Tunis",
        "city": "Tunis",
        "lat": 36.8321,
        "lon": 10.1897,
        "specialties": ["trauma", "cardiac", "general", "neurology"],
        "trauma_bays": 5,
        "available_bays": 3,
        "surgeons_on_call": ["Trauma Surgeon", "Cardiologist", "Neurosurgeon"],
        "equipment": ["Ventilator", "Defibrillator", "CT Scanner", "MRI", "Blood Bank"]
    },
    {
        "name": "Clinique Les Oliviers",
        "city": "Tunis",
        "lat": 36.8412,
        "lon": 10.2156,
        "specialties": ["cardiac", "general"],
        "trauma_bays": 2,
        "available_bays": 2,
        "surgeons_on_call": ["Cardiologist", "General Surgeon"],
        "equipment": ["Defibrillator", "ECG", "Blood Bank"]
    }
]


def find_best_hospital(injury_type: str, location_lat: float = 36.8190, location_lon: float = 10.1660) -> dict:
    """
    Matches injury type to best available hospital
    Returns the most suitable hospital based on specialty and availability
    """
    import math

    def distance(lat1, lon1, lat2, lon2):
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))

    # Determine required specialty
    injury_lower = injury_type.lower()
    if any(w in injury_lower for w in ["cardiac", "heart", "chest pain"]):
        required = "cardiac"
    elif any(w in injury_lower for w in ["head", "brain", "neuro"]):
        required = "neurology"
    elif any(w in injury_lower for w in ["burn"]):
        required = "burns"
    elif any(w in injury_lower for w in ["bone", "fracture", "orthopedic"]):
        required = "orthopedic"
    else:
        required = "trauma"

    # Filter by specialty and availability
    suitable = [
        h for h in TUNISIA_HOSPITALS
        if required in h["specialties"] and h["available_bays"] > 0
    ]

    if not suitable:
        suitable = [h for h in TUNISIA_HOSPITALS if h["available_bays"] > 0]

    if not suitable:
        suitable = TUNISIA_HOSPITALS

    # Sort by distance
    best = min(suitable, key=lambda h: distance(location_lat, location_lon, h["lat"], h["lon"]))
    dist = distance(location_lat, location_lon, best["lat"], best["lon"])

    return {
        "name": best["name"],
        "city": best["city"],
        "lat": best["lat"],
        "lon": best["lon"],
        "distance_km": round(dist, 1),
        "available_bays": best["available_bays"],
        "surgeons_on_call": best["surgeons_on_call"],
        "equipment": best["equipment"],
        "eta_minutes": round(dist * 2.5),
    }