import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# -----------------------
# Env / Config
# -----------------------
load_dotenv()

PORT = int(os.getenv("PORT", "8000"))
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

NEA_WEATHER_URL = os.getenv(
    "NEA_WEATHER_URL",
    "https://api.data.gov.sg/v1/environment/2-hour-weather-forecast",
)
LTA_API_BASE = os.getenv("LTA_API_BASE", "https://datamall2.mytransport.sg/ltaodataservice")
LTA_API_KEY = os.getenv("LTA_API_KEY", "")

TIMEOUT = httpx.Timeout(20.0)

# -----------------------
# App + CORS
# -----------------------
app = FastAPI(title="Smart Travel Companion API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------
# Models (used for /weather output typing)
# -----------------------
class HealthOut(BaseModel):
    status: str
    time_utc: str

class ForecastArea(BaseModel):
    name: str
    forecast: str
    label_location: Optional[Dict[str, Any]] = None  # {"latitude": ..., "longitude": ...}

class WeatherOut(BaseModel):
    updated_at: str
    areas: List[ForecastArea]

# -----------------------
# Helpers
# -----------------------
def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def log(msg: str):
    print(f"[{now_utc_iso()}] {msg}", flush=True)

def normalize_status(val) -> str:
    """Map numeric/status variants to friendly text."""
    if isinstance(val, str):
        s = val.strip()
        return s if s else "Unknown"
    try:
        n = int(val)
    except Exception:
        return str(val)
    mapping = {
        0: "No Service Alert",
        1: "No Service Alert",
        2: "Minor Disruption",
        3: "Major Disruption",
    }
    return mapping.get(n, str(n))

def normalize_message(val) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, str):
        s = val.strip()
        return s or None
    if isinstance(val, (list, tuple)):
        flat = []
        for x in val:
            flat.append(x if isinstance(x, str) else str(x))
        s = " ".join([t.strip() for t in flat if t and str(t).strip()])
        return s or None
    if isinstance(val, dict):
        # Prefer common keys if present
        for k in ("Message", "Detail", "Description", "Remarks"):
            v = val.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return str(val)
    return str(val)

SUPPORTED_LINES = {"CCL","CEL","CGL","DTL","EWL","NEL","NSL","BPL","SLRT","PLRT","TEL"}

def coerce_list(val):
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]

def to_str(v):
    if v is None:
        return None
    return v if isinstance(v, str) else str(v)

# -----------------------
# Global exception handler (so CORS headers still apply)
# -----------------------
@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    log(f"UNHANDLED ERROR: {exc!r}")
    return JSONResponse(
        status_code=500,
        content={"ok": False, "error": "internal_server_error", "detail": str(exc)},
    )

# -----------------------
# Utility endpoints
# -----------------------
@app.get("/")
async def root():
    return {"ok": True, "project": "smart-travel", "version": "0.2.0"}

@app.get("/config")
async def config():
    return {
        "allowed_origins": ALLOWED_ORIGINS,
        "nea_weather_url": NEA_WEATHER_URL,
        "lta_api_base": LTA_API_BASE,
        "lta_api_key_configured": bool(LTA_API_KEY),
    }

@app.get("/routes")
async def routes():
    return sorted([r.path for r in app.router.routes])

@app.get("/health", response_model=HealthOut)
async def health():
    return HealthOut(status="ok", time_utc=now_utc_iso())

# -----------------------
# Weather
# -----------------------
@app.get("/weather", response_model=WeatherOut)
async def get_weather():
    log("GET /weather")
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(NEA_WEATHER_URL)
            r.raise_for_status()
            data = r.json()
            log(f"/weather upstream ok status={r.status_code}")
    except Exception as e:
        log(f"/weather upstream error: {e!r}")
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
        log("/weather: no items")
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
        areas.append(
            ForecastArea(
                name=name,
                forecast=f.get("forecast", "Unknown"),
                label_location=coords_map.get(name),
            )
        )

    return WeatherOut(updated_at=updated_at, areas=sorted(areas, key=lambda x: x.name.lower()))

# -----------------------
# MRT service alerts (normalized + has_disruption)
# -----------------------
@app.get("/mrt")
async def get_mrt():
    log("GET /mrt")

    if not LTA_API_KEY:
        log("/mrt: missing LTA_API_KEY")
        return {
            "ok": True,
            "source": "LTA Datamall",
            "updated_at": now_utc_iso(),
            "has_disruption": False,
            "alerts": [
                {"line": "ALL", "status": "MissingKey", "message": "Set LTA_API_KEY in backend/.env",
                 "timestamp": None, "direction": None, "stations": None, "bus_shuttle": None}
            ],
        }

    url = f"{LTA_API_BASE}/TrainServiceAlerts"
    headers = {"AccountKey": LTA_API_KEY, "accept": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=headers) as client:
            r = await client.get(url)
            status = r.status_code
            text = r.text
            log(f"/mrt upstream status={status}")
            if status != 200:
                return {
                    "ok": False,
                    "source": "LTA Datamall",
                    "updated_at": now_utc_iso(),
                    "error": {"status": status, "body": text[:800]},
                    "has_disruption": None,
                    "alerts": [],
                }
            data = r.json()
    except Exception as e:
        log(f"/mrt upstream exception: {e!r}")
        return {
            "ok": False,
            "source": "LTA Datamall",
            "updated_at": now_utc_iso(),
            "error": {"exception": str(e)},
            "has_disruption": None,
            "alerts": [],
        }

    raw = data.get("value")
    temp_alerts: List[Dict[str, Any]] = []

    # A) list (usually dicts)
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                temp_alerts.append(
                    {
                        "line": item.get("Line", "Unknown"),
                        "status": item.get("Status", "Unknown"),
                        "message": item.get("Message"),
                        "timestamp": item.get("CreatedDate"),
                        "direction": item.get("Direction"),
                        "stations": item.get("AffectedStations"),
                        "bus_shuttle": item.get("BusShuttle"),
                    }
                )
            elif isinstance(item, str):
                temp_alerts.append({"line": "ALL", "status": item, "message": None,
                                    "timestamp": None, "direction": None, "stations": None, "bus_shuttle": None})

    # B) single dict
    elif isinstance(raw, dict):
        temp_alerts.append(
            {
                "line": raw.get("Line", "Unknown"),
                "status": raw.get("Status", "Unknown"),
                "message": raw.get("Message"),
                "timestamp": raw.get("CreatedDate"),
                "direction": raw.get("Direction"),
                "stations": raw.get("AffectedStations"),
                "bus_shuttle": raw.get("BusShuttle"),
            }
        )

    # C) plain string (e.g., "No Service Alert")
    elif isinstance(raw, str):
        temp_alerts.append({"line": "ALL", "status": raw, "message": None,
                            "timestamp": None, "direction": None, "stations": None, "bus_shuttle": None})

    else:
        log(f"/mrt unexpected payload type: {type(raw).__name__}")
        return {
            "ok": False,
            "source": "LTA Datamall",
            "updated_at": now_utc_iso(),
            "error": {"reason": "unexpected_payload", "type": type(raw).__name__},
            "has_disruption": None,
            "alerts": [],
            "raw": data,
        }

    # Normalize for UI
    normalized_alerts: List[Dict[str, Any]] = []
    for a in temp_alerts:
        normalized_alerts.append({
            "line": a.get("line", "Unknown"),
            "status": normalize_status(a.get("status")),
            "message": normalize_message(a.get("message")),
            "timestamp": a.get("timestamp"),
            "direction": a.get("direction"),
            "stations": a.get("stations"),
            "bus_shuttle": a.get("bus_shuttle"),
        })

    has_disruption = any(
        (x.get("status") or "").strip() not in ("No Service Alert", "Normal", "All Clear")
        for x in normalized_alerts
    )

    return {
        "ok": True,
        "source": "LTA Datamall",
        "updated_at": now_utc_iso(),
        "has_disruption": has_disruption,
        "alerts": normalized_alerts,
    }

# -----------------------
# MRT crowdedness (real-time)
# -----------------------
@app.get("/mrt/crowd")
async def mrt_crowd(line: str = Query("NSL", min_length=2, max_length=5)):
    line = line.upper().strip()
    if line not in SUPPORTED_LINES:
        return {"ok": False, "error": "invalid_line", "supported": sorted(SUPPORTED_LINES)}

    url = f"{LTA_API_BASE}/PCDRealTime"
    headers = {"AccountKey": LTA_API_KEY, "accept": "application/json"}
    params = {"TrainLine": line}

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=headers, params=params) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return {"ok": False, "status": r.status_code, "body": r.text[:800]}
            data = r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

    rows = coerce_list(data.get("value"))
    out = []
    for item in rows:
        if isinstance(item, dict):
            out.append({
                "station_code": to_str(item.get("StationCode") or item.get("Station_id") or item.get("Code")),
                "station": to_str(item.get("Station") or item.get("StationName")),
                "crowd_level": to_str(item.get("CrowdLevel") or item.get("Crowd") or item.get("Load")),
                "last_update": to_str(item.get("LastUpdate") or item.get("AsAt") or item.get("Timestamp")),
            })
        elif isinstance(item, str):
            out.append({"station_code": None, "station": None, "crowd_level": item, "last_update": None})

    return {
        "ok": True,
        "source": "LTA Datamall",
        "line": line,
        "updated_at": now_utc_iso(),
        "stations": out
    }

# -----------------------
# MRT crowdedness (forecast)
# -----------------------
@app.get("/mrt/crowd-forecast")
async def mrt_crowd_forecast(line: str = Query("NSL", min_length=2, max_length=5)):
    line = line.upper().strip()
    if line not in SUPPORTED_LINES:
        return {"ok": False, "error": "invalid_line", "supported": sorted(SUPPORTED_LINES)}

    url = f"{LTA_API_BASE}/PCDForecast"
    headers = {"AccountKey": LTA_API_KEY, "accept": "application/json"}
    params = {"TrainLine": line}

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=headers, params=params) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return {"ok": False, "status": r.status_code, "body": r.text[:800]}
            data = r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

    rows = coerce_list(data.get("value"))
    out = []
    for item in rows:
        if isinstance(item, dict):
            out.append({
                "station_code": to_str(item.get("StationCode")),
                "station": to_str(item.get("Station") or item.get("StationName")),
                "time_slot": to_str(item.get("TimeSlot") or item.get("Time") or item.get("DateTime")),
                "crowd_level": to_str(item.get("CrowdLevel") or item.get("Crowd")),
            })
        elif isinstance(item, str):
            out.append({"station_code": None, "station": None, "time_slot": None, "crowd_level": item})

    return {
        "ok": True,
        "source": "LTA Datamall",
        "line": line,
        "updated_at": now_utc_iso(),
        "forecast": out
    }

# -----------------------
# Entrypoint
# -----------------------
if __name__ == "__main__":
    import uvicorn
    log("Starting Uvicorn...")
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
