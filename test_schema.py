import json
from pydantic import BaseModel, Field

class TriageResult(BaseModel):
    diagnosis_priority: str = Field(description="High, Medium, or Low priority based on symptoms")
    referral: str = Field(description="Suggested next steps (e.g., 'Go to ER immediately', 'Schedule PCP appointment', 'Rest and hydrate')")
    symptom_checklist: list[str] = Field(description="List of detected symptoms")
    nearest_er: str = Field(description="Placeholder text indicating to check local maps for nearest facility")
    pre_fill_form: dict[str, str] = Field(description="Pre-filled patient intake form fields extracted from text, like Age, Gender, Primary Complaint, Duration")

print(json.dumps(TriageResult.model_json_schema(), indent=2))
