from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# Define complaint model
class Complaint(BaseModel):
    text: str
    location: str

# Simple classifier (reuse your function)
def classify_complaint(text: str):
    text = text.lower()
    if "garbage" in text or "trash" in text:
        return {"Category": "Sanitation", "Department": "Waste Management", "Urgency": "High"}
    elif "streetlight" in text or "light" in text:
        return {"Category": "Infrastructure", "Department": "Electrical Department", "Urgency": "Medium"}
    elif "water" in text or "leak" in text:
        return {"Category": "Water Supply", "Department": "Water Department", "Urgency": "High"}
    elif "traffic" in text or "signal" in text:
        return {"Category": "Traffic", "Department": "Traffic Department", "Urgency": "Medium"}
    else:
        return {"Category": "General Complaint", "Department": "City Services", "Urgency": "Low"}

# API endpoint
@app.post("/complaints/")
def submit_complaint(complaint: Complaint):
    result = classify_complaint(complaint.text)
    return {"complaint": complaint.text, "location": complaint.location, "analysis": result}