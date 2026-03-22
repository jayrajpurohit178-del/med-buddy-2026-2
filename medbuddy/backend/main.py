from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import aiofiles
import os
import json

from gemini_service import process_text, process_image, process_audio, process_medication_photo
from scheduler import schedule_reminders, start_scheduler, stop_scheduler, get_scheduled_reminders

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

prescription_history = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()

app = FastAPI(title="MedBuddy API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "MedBuddy API is running"}

@app.post("/api/process/text")
async def process_text_endpoint(
    text: str = Form(...),
    patient_age: str = Form(default=""),
    language: str = Form(default="English")
):
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    result = await process_text(text, patient_age, language)
    if "medications" in result:
        prescription_history.extend(result["medications"])
    return JSONResponse(content=result)

@app.post("/api/process/file")
async def process_file_endpoint(
    file: UploadFile = File(...),
    patient_age: str = Form(default=""),
    language: str = Form(default="English")
):
    file_bytes = await file.read()
    mime_type = file.content_type or "application/octet-stream"

    if mime_type == "application/pdf":
        result = await process_image(file_bytes, "application/pdf", patient_age, language)
    elif mime_type.startswith("image/"):
        result = await process_image(file_bytes, mime_type, patient_age, language)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {mime_type}")

    if "medications" in result:
        prescription_history.extend(result["medications"])
    return JSONResponse(content=result)

@app.post("/api/process/audio")
async def process_audio_endpoint(
    file: UploadFile = File(...),
    patient_age: str = Form(default=""),
    language: str = Form(default="English")
):
    file_bytes = await file.read()
    mime_type = file.content_type or "audio/mpeg"
    result = await process_audio(file_bytes, mime_type, patient_age, language)
    if "medications" in result:
        prescription_history.extend(result["medications"])
    return JSONResponse(content=result)

@app.post("/api/process/medication-photo")
async def process_medication_photo_endpoint(
    file: UploadFile = File(...)
):
    file_bytes = await file.read()
    mime_type = file.content_type or "image/jpeg"
    result = await process_medication_photo(file_bytes, mime_type, prescription_history)
    return JSONResponse(content=result)

@app.post("/api/schedule-reminders")
async def schedule_reminders_endpoint(
    medications: str = Form(...),
    phone: str = Form(...),
    whatsapp: str = Form(default="")
):
    try:
        meds = json.loads(medications)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid medications JSON")
    scheduled = schedule_reminders(meds, phone, whatsapp)
    return JSONResponse(content={"scheduled": scheduled, "count": len(scheduled)})

@app.get("/api/reminders")
async def get_reminders():
    return JSONResponse(content=get_scheduled_reminders())

@app.get("/api/history")
async def get_history():
    return JSONResponse(content=prescription_history)