from google import genai
from google.genai import types
import os
import base64
import json
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-1.5-flash"

SYSTEM_PROMPT = """You are MedBuddy, a medical document simplifier. Read prescriptions and discharge summaries and extract information EXACTLY as written by the doctor.

STRICT RULES:
1. NEVER add medical advice not present in the document
2. NEVER suggest alternative medicines
3. NEVER bring in outside medical information
4. Extract dosage and timing EXACTLY as written - wrong values are a patient safety failure
5. If something is unclear, say "unclear in document" — do not guess

Respond ONLY with a valid JSON object, no markdown, no extra text."""

def build_prompt(patient_age: str = "", language: str = "English"):
    age_note = f"The patient is {patient_age} years old." if patient_age else ""
    lang_note = f"Respond in {language}." if language == "Hindi" else ""
    return f"""{SYSTEM_PROMPT}
{age_note} {lang_note}

Return this exact JSON:
{{
  "one_line_summary": "One sentence a family member can understand",
  "diagnosis": {{
    "condition": "Condition name in plain language",
    "plain_explanation": "Explained like talking to a friend, 2-3 sentences"
  }},
  "medications": [
    {{
      "name": "Medicine name exactly as written",
      "dosage": "Dosage exactly as written",
      "timing": "Timing exactly as written",
      "duration": "Duration exactly as written",
      "with_food": "yes/no/not specified"
    }}
  ],
  "side_effects": [
    {{
      "medicine": "Medicine name",
      "watch_for": ["symptom 1", "symptom 2"],
      "call_doctor_if": "Warning condition"
    }}
  ],
  "followup_checklist": {{
    "tests_ordered": ["test 1"],
    "diet_restrictions": ["restriction 1"],
    "activity_limits": ["limit 1"],
    "next_appointment": "Date if mentioned"
  }}
}}"""

async def process_text(text: str, patient_age: str = "", language: str = "English") -> dict:
    prompt = build_prompt(patient_age, language)
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt + f"\n\nDOCUMENT TEXT:\n{text}"
    )
    return parse_response(response.text)

async def process_image(image_bytes: bytes, mime_type: str, patient_age: str = "", language: str = "English") -> dict:
    prompt = build_prompt(patient_age, language)
    response = client.models.generate_content(
        model=MODEL,
        contents=[
            prompt + "\n\nExtract all text from this prescription image and process it:",
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        ]
    )
    return parse_response(response.text)

async def process_audio(audio_bytes: bytes, mime_type: str, patient_age: str = "", language: str = "English") -> dict:
    prompt = build_prompt(patient_age, language)
    response = client.models.generate_content(
        model=MODEL,
        contents=[
            prompt + "\n\nThis is a doctor-patient audio recording. Transcribe and extract prescription info:",
            types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
        ]
    )
    return parse_response(response.text)

async def process_medication_photo(image_bytes: bytes, mime_type: str, history: list) -> dict:
    history_text = json.dumps(history, indent=2) if history else "No history."
    response = client.models.generate_content(
        model=MODEL,
        contents=[
            f"""Identify medications in this photo. Return ONLY valid JSON:
{{
  "identified_medicines": ["medicine name"],
  "matched_from_history": [
    {{
      "medicine": "name",
      "dosage": "from history",
      "timing": "from history",
      "duration": "from history"
    }}
  ],
  "not_in_history": ["medicine not in history"]
}}
Patient history:
{history_text}
Only match medicines from history — do not add new information.""",
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        ]
    )
    return parse_response(response.text)

def parse_response(text: str) -> dict:
    try:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        return json.loads(cleaned.strip())
    except json.JSONDecodeError:
        return {"error": "Could not parse AI response", "raw": text}