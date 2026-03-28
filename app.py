import os
import json
import base64
import logging
from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("medbridge")

# Try to use Google Cloud Logging in production
try:
    import google.cloud.logging as cloud_logging
    cloud_client = cloud_logging.Client()
    cloud_client.setup_logging()
    logger.info("Google Cloud Logging enabled")
except Exception:
    logger.info("Running with local logging (Cloud Logging not available)")

app = Flask(__name__)

# ── Rate Limiting ──────────────────────────────────────────────────────────────
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# ── Gemini Client (Cached Singleton) ──────────────────────────────────────────
_gemini_client = None

def get_client():
    """Returns a cached Gemini client, creating it only once."""
    global _gemini_client
    if _gemini_client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client

# ── Pydantic Schemas ───────────────────────────────────────────────────────────
ALLOWED_LANGUAGES = {
    "English", "Hindi", "Bengali", "Telugu", "Marathi", "Tamil", "Urdu",
    "Gujarati", "Kannada", "Odia", "Malayalam", "Punjabi", "Sanskrit",
    "Spanish", "French", "Arabic", "Mandarin", "German", "Japanese",
    "Portuguese", "Russian"
}

class PreFillForm(BaseModel):
    Age: str | None = Field(default=None, description="Patient's age")
    Gender: str | None = Field(default=None, description="Patient's gender")
    Primary_Complaint: str | None = Field(default=None, description="Primary complaint", alias="Primary Complaint")
    Duration: str | None = Field(default=None, description="Duration of symptoms")
    Medical_History: str | None = Field(default=None, description="Relevant medical history", alias="Medical History")
    Allergies: str | None = Field(default=None, description="Known allergies")

class TriageResult(BaseModel):
    diagnosis_priority: str = Field(description="High, Medium, or Low priority based on symptoms")
    referral: str = Field(description="Suggested next steps (e.g., 'Go to ER immediately', 'Schedule PCP appointment')")
    symptom_checklist: list[str] = Field(description="List of detected symptoms")
    nearest_er: str = Field(description="Placeholder text for local facility")
    pre_fill_form: PreFillForm = Field(description="Pre-filled patient intake form fields")
    language_detected: str = Field(description="The language the user input was in (e.g., 'English', 'Hindi', 'Spanish')")
    translated_referral: str = Field(description="The 'referral' translated into the detected language above")

# ── Security Headers Middleware ────────────────────────────────────────────────
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(self), microphone=(self)'
    return response

# ── Routes ─────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    maps_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    return render_template('index.html', maps_api_key=maps_key)

@app.route('/api/health')
def health():
    """Health check endpoint for Cloud Run readiness probes."""
    return jsonify({"status": "ok", "service": "medbridge-ai", "version": "3.1"}), 200

@app.route('/api/analyze', methods=['POST'])
@limiter.limit("10 per minute")
def analyze():
    data = request.json
    if not data or ('text' not in data and 'image' not in data):
        logger.warning("Request rejected: No input provided")
        return jsonify({"error": "No input provided"}), 400

    user_text = data.get('text', '').strip()
    image_b64 = data.get('image')
    target_lang = data.get('target_language', 'English')

    # ── Input Validation ─────────────────────────────────────────────────────
    if target_lang not in ALLOWED_LANGUAGES:
        logger.warning(f"Invalid target_language: {target_lang!r}")
        target_lang = 'English'

    if len(user_text) > 5000:
        return jsonify({"error": "Input text is too long (max 5000 characters)"}), 400

    if image_b64 and len(image_b64) > 10_000_000:  # ~7.5MB base64
        return jsonify({"error": "Image is too large (max ~7.5MB)"}), 400

    # Check if API key is set, else return demo/mock data
    client = get_client()
    if not client:
        logger.warning("API key not configured — returning demo data")
        return jsonify({
            "diagnosis_priority": "High",
            "referral": f"Go to nearest ER (Demo Mode — configure GEMINI_API_KEY)",
            "symptom_checklist": ["Chest pain", "Shortness of breath"],
            "nearest_er": "City General Hospital",
            "pre_fill_form": {"Primary Complaint": "Emergency (Demo)"},
            "language_detected": "English",
            "translated_referral": "Emergency"
        })

    try:
        contents = []
        if user_text:
            contents.append(f"User Description: {user_text}")
        if image_b64:
            if ',' in image_b64:
                image_b64 = image_b64.split(',')[1]
            image_bytes = base64.b64decode(image_b64)
            contents.append(types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"))

        logger.info(f"Processing request: lang={target_lang}, has_text={bool(user_text)}, has_image={bool(image_b64)}")

        # Generate structured content using Gemini 2.5 Flash
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                "You are a highly advanced medical AI triage system. "
                "Analyze the following messy, unstructured user input (text and/or image) and convert it into a structured triage result. "
                f"IMPORTANT: The user has requested the results in {target_lang}. "
                f"You MUST provide ALL string values (referral, symptoms, form keys, and form values) in {target_lang}. "
                "Detect the source language of the input for the 'language_detected' field.",
                *contents
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=TriageResult,
                temperature=0.2,
            )
        )

        result_json = response.text
        parsed = json.loads(result_json)
        logger.info(f"Successfully processed triage request: priority={parsed.get('diagnosis_priority')}")
        return jsonify(parsed)

    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}", exc_info=True)
        return jsonify({"error": "Analysis failed. Please try again."}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "production") == "development"
    app.run(host='0.0.0.0', port=port, debug=debug)
