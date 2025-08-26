from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class HealthOut(BaseModel):
    status: str
    time_utc: str

class ForecastArea(BaseModel):
    name: str
    forecast: str
    label_location: Optional[Dict[str, Any]] = None

class WeatherOut(BaseModel):
    updated_at: str
    areas: List[ForecastArea]
