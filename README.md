# MedBridge - Universal Health Intent Translator

A Gemini-powered application that solves for societal benefit by acting as a universal bridge between human intent and complex medical triage systems. It takes unstructured, messy, real-world inputs (like a messy stack of medical history) and instantly converts them into structured, verified, and life-saving actions.

## Vertical Chosen: Medical Health Triage Navigator
The solution leverages Gemini 2.5 Flash to act as a triage system, interpreting chaotic symptom descriptions and categorizing them into:
1. Diagnosis Priority (High/Medium/Low)
2. Immediate Referral / Action
3. Symptom Checklists
4. Pre-filled structured intake forms for the hospital

## Approach and Logic
- **Unstructured Input:** The user types (or simulates voice) their symptoms or medical history.
- **Gemini Processing:** The backend hits the Gemini AI using the `google-genai` library, passing the input alongside an advanced prompt that requests a highly structured JSON response matching a Pydantic schema.
- **Structured Rendering:** The UI dynamically parses the resulting JSON and renders it into actionable cards, ensuring clarity and prioritizing potentially life-saving recommendations.

## How it works (Demo Mode vs Live API)
If the `GEMINI_API_KEY` is not present, the app safely falls back to a realistic "Demo Mode" mock response to ensure the hackathon demonstration is fault-proof even without API keys in the environment.

## Installation / Usage
```bash
git clone <your-repo-link>
cd medbridge
pip install -r requirements.txt
export GEMINI_API_KEY="your_api_key_here"  # Optional for Demo Mode
python app.py
```
Open http://localhost:5000 in your browser!
