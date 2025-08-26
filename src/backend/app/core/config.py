import os
from dotenv import load_dotenv

load_dotenv()

PORT = int(os.getenv("PORT", "8000"))
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
NEA_WEATHER_URL = os.getenv("NEA_WEATHER_URL", "https://api.data.gov.sg/v1/environment/2-hour-weather-forecast")
LTA_API_BASE = os.getenv("LTA_API_BASE", "https://datamall2.mytransport.sg/ltaodataservice")
LTA_API_KEY = os.getenv("LTA_API_KEY", "")

def cfg_summary():
    return {
        "allowed_origins": ALLOWED_ORIGINS,
        "nea_weather_url": NEA_WEATHER_URL,
        "lta_api_base": LTA_API_BASE,
        "lta_api_key_configured": bool(LTA_API_KEY),
    }
