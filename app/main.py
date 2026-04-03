from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
from app.pipeline import analyze_emergency_scene

app = FastAPI(
    title = "Zero-Minute Dispatch API",
    description="AI powered emergecy triage system",
    version = "1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_methods = ["*"],
    allow_headers = ["*"],
)

@app.get("/health")
def health_check():
    return {"status": "operational" , "system": "Zero-Minute Dispatch"}

@app.post("/analyze")
async def analyze_scene(video: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False , suffix=".mp4") as tmp:
        content = await video.read()
        tmp.write(content)
        tmp_path = tmp.name 
    try:
        report = analyze_emergency_scene(tmp_path)
        return report.model_dump()
    finally:
        os.unlink(tmp_path)