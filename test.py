import os
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class TriageResult(BaseModel):
    diagnosis_priority: str = Field(description="High, Medium, or Low priority based on symptoms")
    referral: str = Field(description="Suggested next steps (e.g., 'Go to ER immediately', 'Schedule PCP appointment', 'Rest and hydrate')")
    symptom_checklist: list[str] = Field(description="List of detected symptoms")
    nearest_er: str = Field(description="Placeholder text indicating to check local maps for nearest facility")
    pre_fill_form: dict[str, str] = Field(description="Pre-filled patient intake form fields extracted from text, like Age, Gender, Primary Complaint, Duration")

try:
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents="conscious but very confused, keeps asking what happened. There is heavy bleeding from his head and his right leg looks twisted in a wrong direction. He said his name is Rajan. He is diabetic and takes metformin. He is allergic to penicillin. Accident happened about 15 minutes ago.",
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TriageResult,
            temperature=0.2,
        )
    )
    print("SUCCESS")
    print(response.text)
except Exception as e:
    print("FAILED:", repr(e))
