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

class TriageResult(BaseModel):
    diagnosis_priority: str = Field(description="High, Medium, or Low priority based on symptoms")
    referral: str = Field(description="Suggested next steps (e.g., 'Go to ER immediately', 'Schedule PCP appointment', 'Rest and hydrate')")
    symptom_checklist: list[str] = Field(description="List of detected symptoms")
    nearest_er: str = Field(description="Placeholder text indicating to check local maps for nearest facility")
    pre_fill_form: dict[str, str] = Field(description="Pre-filled patient intake form fields extracted from text, like Age, Gender, Primary Complaint, Duration")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json
    if not data or 'text' not in data:
        return jsonify({"error": "No text provided"}), 400
        
    user_text = data['text']
    
    # Check if API key is set, else return mock data (demo mode)
    client = get_client()
    if not client:
        print("Running in DEMO mode (No API Key found)")
        return jsonify({
            "diagnosis_priority": "High",
            "referral": "Go to nearest ER immediately",
            "symptom_checklist": ["Chest pain", "Shortness of breath (simulated)"],
            "nearest_er": "City General Hospital (Demo)",
            "pre_fill_form": {
                "Primary Complaint": "Chest pain",
                "Patient Notes": user_text
            }
        })

    try:
        # Generate structured content using Gemini 2.5 Flash
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"""
                You are a highly advanced medical AI triage system. 
                Analyze the following messy, unstructured user input and convert it into a structured triage result.
                
                User Input: "{user_text}"
            """,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=TriageResult,
                temperature=0.2,
            )
        )
        
        result_json = response.text
        # Safety check to ensure it's parseable
        parsed = json.loads(result_json)
        return jsonify(parsed)
        
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return jsonify({"error": "Failed to analyze data"}), 500

if __name__ == '__main__':
    # Run slightly differently for development
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
