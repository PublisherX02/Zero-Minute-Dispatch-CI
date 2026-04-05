from fastapi import FastAPI, UploadFile, File, Form
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import tempfile
import os
import json as json_module
from app.pipeline import analyze_emergency_scene, analyze_emergency_scene_stream

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

@app.post("/analyze/stream")
async def analyze_scene_stream(
    file: UploadFile = File(...),
    location: Optional[str] = Form(None)
):
    filename = file.filename.lower()
    if filename.endswith(".mp3") or filename.endswith(".wav") or filename.endswith(".m4a"):
        suffix = "." + filename.split(".")[-1]
    else:
        suffix = ".mp4"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    async def generate():
        try:
            for item in analyze_emergency_scene_stream(tmp_path, location):
                if isinstance(item, dict):
                    # Final fully-processed report — signals stream completion
                    yield f"data: [DONE]{json_module.dumps(item)}\n\n"
                else:
                    # Raw Gemini text chunk
                    yield f"data: {item}\n\n"
        finally:
            os.unlink(tmp_path)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@app.post("/analyze")
async def analyze_scene(file: UploadFile = File(...), location: Optional[str] = Form(None)):
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
        report = analyze_emergency_scene(tmp_path, location=location)
        return report.model_dump()
    finally:
        os.unlink(tmp_path)