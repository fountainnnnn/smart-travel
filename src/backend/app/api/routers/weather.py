from fastapi import APIRouter
from ...schemas.common import WeatherOut
from ...services.nea import fetch_weather

router = APIRouter()

@router.get("/weather", response_model=WeatherOut)
async def weather() -> WeatherOut:
    return await fetch_weather()
