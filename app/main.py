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
async def analyze_scene(file: UploadFile = File(...)):
    # Detect file type
    filename = file.filename.lower()
    
    if filename.endswith('.mp3') or filename.endswith('.wav') or filename.endswith('.m4a'):
        suffix = "." + filename.split(".")[-1]
    else:
        suffix = ".mp4"
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        report = analyze_emergency_scene(tmp_path)
        return report.model_dump()
    finally:
        os.unlink(tmp_path)