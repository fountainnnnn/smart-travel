from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.utils.config import load_config

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

cfg = load_config()

@app.get("/health")
def health():
    return {"ok": True, "project": cfg["project"]}


from pydantic import BaseModel
from datetime import datetime

class PredictRequest(BaseModel):
    origin: str
    destination: str
    depart_at: datetime

@app.post("/predict")
def predict(req: PredictRequest):
    # stub until models are trained
    return {
        "rain": {"class": "high", "prob": 0.77},
        "crowd": {"class": "heavy", "prob": 0.69},
        "advice": "Suggest leaving ~20 min earlier."
    }
