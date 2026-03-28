import json
from pydantic import BaseModel, Field
from typing import Dict, Any

class TriageResultDict(BaseModel):
    pre_fill_form: dict = Field(description="Pre-filled patient intake form fields extracted from text, like Age, Gender, Primary Complaint, Duration")

class IntakeForm(BaseModel):
    age: str | None = Field(default=None)
    gender: str | None = Field(default=None)
    primary_complaint: str | None = Field(default=None)
    duration: str | None = Field(default=None)

class TriageResultModel(BaseModel):
    pre_fill_form: IntakeForm = Field(description="Pre-filled patient intake form fields extracted from text")

print("DICT:")
print(json.dumps(TriageResultDict.model_json_schema(), indent=2))
print("MODEL:")
print(json.dumps(TriageResultModel.model_json_schema(), indent=2))
