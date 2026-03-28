import os
import json
from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Initialize Gemini Client Lazy-Loader
def get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

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

@app.route('/')
def index():
    maps_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    return render_template('index.html', maps_api_key=maps_key)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json
    if not data or ('text' not in data and 'image' not in data):
        return jsonify({"error": "No input provided"}), 400
        
    user_text = data.get('text', '')
    image_b64 = data.get('image')
    target_lang = data.get('target_language', 'English')
    
    # Check if API key is set, else return mock data
    client = get_client()
    if not client:
        return jsonify({
            "diagnosis_priority": "High",
            "referral": f"Go to nearest ER (Mocked in {target_lang})",
            "symptom_checklist": ["Chest pain"],
            "nearest_er": "City General Hospital",
            "pre_fill_form": {"Primary Complaint": "Emergency"},
            "language_detected": "English",
            "translated_referral": "Emergency"
        })

    try:
        contents = []
        import base64
        if user_text:
            contents.append(f"User Description: {user_text}")
        if image_b64:
            if ',' in image_b64:
                image_b64 = image_b64.split(',')[1]
            image_bytes = base64.b64decode(image_b64)
            contents.append(types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"))

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
        return jsonify(parsed)
        
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return jsonify({"error": str(e)}), 500
        
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return jsonify({"error": "Failed to analyze data"}), 500

if __name__ == '__main__':
    # Run slightly differently for development
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
