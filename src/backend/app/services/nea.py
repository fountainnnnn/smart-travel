from typing import Dict, Any, List
from datetime import datetime, timezone
from ..core.config import NEA_WEATHER_URL
from ..core.http import get_client
from ..schemas.common import ForecastArea, WeatherOut

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

async def fetch_weather() -> WeatherOut:
    try:
        async with get_client() as client:
            r = await client.get(NEA_WEATHER_URL)
            r.raise_for_status()
            data = r.json()
    except Exception:
        # Friendly fallback
        return WeatherOut(
            updated_at=now_utc_iso(),
            areas=[
                ForecastArea(name="Ang Mo Kio", forecast="Light Rain"),
                ForecastArea(name="Bedok", forecast="Cloudy"),
                ForecastArea(name="Bishan", forecast="Fair"),
            ],
        )

    items = data.get("items", [])
    area_meta = data.get("area_metadata", []) or []
    if not items:
        return WeatherOut(updated_at=now_utc_iso(), areas=[ForecastArea(name="Unknown", forecast="Unknown")])

    latest = items[0]
    updated_at = latest.get("update_timestamp") or latest.get("timestamp") or now_utc_iso()
    forecasts = latest.get("forecasts", [])

    coords_map: Dict[str, Dict[str, Any]] = {}
    for m in area_meta:
        name = m.get("name")
        loc = m.get("label_location") or m.get("location")
        if name and isinstance(loc, dict):
            coords_map[name] = {"latitude": loc.get("latitude"), "longitude": loc.get("longitude")}

    areas: List[ForecastArea] = []
    for f in forecasts:
        name = f.get("area", "Unknown")
        areas.append(ForecastArea(name=name, forecast=f.get("forecast", "Unknown"), label_location=coords_map.get(name)))

    return WeatherOut(updated_at=updated_at, areas=sorted(areas, key=lambda x: x.name.lower()))
