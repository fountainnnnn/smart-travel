from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import math
from ..core.config import LTA_API_BASE, LTA_API_KEY
from ..core.http import get_client

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def normalize_status(val) -> str:
    if isinstance(val, str):
        s = val.strip()
        return s if s else "Unknown"
    try:
        n = int(val)
    except Exception:
        return str(val)
    return {0: "No Service Alert", 1: "No Service Alert", 2: "Minor Disruption", 3: "Major Disruption"}.get(n, str(n))

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
        for k in ("Message", "Detail", "Description", "Remarks"):
            v = val.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return str(val)
    return str(val)

SUPPORTED_LINES = {"CCL","CEL","CGL","DTL","EWL","NEL","NSL","BPL","SLRT","PLRT","TEL"}

# -------- MRT alerts --------
async def get_mrt_alerts():
    if not LTA_API_KEY:
        return {
            "ok": True, "source": "LTA Datamall", "updated_at": now_utc_iso(), "has_disruption": False,
            "alerts": [{"line":"ALL","status":"MissingKey","message":"Set LTA_API_KEY in backend/.env",
                        "timestamp":None,"direction":None,"stations":None,"bus_shuttle":None}]
        }

    url = f"{LTA_API_BASE}/TrainServiceAlerts"
    headers = {"AccountKey": LTA_API_KEY, "accept": "application/json"}

    try:
        async with get_client(headers=headers) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return {"ok": False, "source": "LTA Datamall", "updated_at": now_utc_iso(),
                        "error":{"status":r.status_code,"body":r.text[:800]}, "has_disruption": None, "alerts": []}
            data = r.json()
    except Exception as e:
        return {"ok": False, "source": "LTA Datamall", "updated_at": now_utc_iso(),
                "error":{"exception":str(e)}, "has_disruption": None, "alerts": []}

    raw = data.get("value")
    temp: List[Dict[str, Any]] = []

    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                temp.append({
                    "line": item.get("Line","Unknown"),
                    "status": item.get("Status","Unknown"),
                    "message": item.get("Message"),
                    "timestamp": item.get("CreatedDate"),
                    "direction": item.get("Direction"),
                    "stations": item.get("AffectedStations"),
                    "bus_shuttle": item.get("BusShuttle"),
                })
            elif isinstance(item, str):
                temp.append({"line":"ALL","status":item,"message":None,"timestamp":None,
                             "direction":None,"stations":None,"bus_shuttle":None})
    elif isinstance(raw, dict):
        temp.append({
            "line": raw.get("Line","Unknown"),
            "status": raw.get("Status","Unknown"),
            "message": raw.get("Message"),
            "timestamp": raw.get("CreatedDate"),
            "direction": raw.get("Direction"),
            "stations": raw.get("AffectedStations"),
            "bus_shuttle": raw.get("BusShuttle"),
        })
    elif isinstance(raw, str):
        temp.append({"line":"ALL","status":raw,"message":None,"timestamp":None,
                     "direction":None,"stations":None,"bus_shuttle":None})
    else:
        return {"ok": False, "source": "LTA Datamall", "updated_at": now_utc_iso(),
                "error":{"reason":"unexpected_payload","type":type(raw).__name__}, "has_disruption": None, "alerts": [], "raw": data}

    alerts = [{
        "line": a.get("line","Unknown"),
        "status": normalize_status(a.get("status")),
        "message": normalize_message(a.get("message")),
        "timestamp": a.get("timestamp"),
        "direction": a.get("direction"),
        "stations": a.get("stations"),
        "bus_shuttle": a.get("bus_shuttle"),
    } for a in temp]

    has_disruption = any((x.get("status") or "").strip() not in ("No Service Alert","Normal","All Clear") for x in alerts)
    return {"ok": True, "source":"LTA Datamall", "updated_at": now_utc_iso(), "has_disruption": has_disruption, "alerts": alerts}

# -------- MRT crowd --------
async def get_mrt_crowd(line: str):
    url = f"{LTA_API_BASE}/PCDRealTime"
    headers = {"AccountKey": LTA_API_KEY, "accept": "application/json"}
    params = {"TrainLine": line}
    try:
        async with get_client(headers=headers, params=params) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return {"ok": False, "status": r.status_code, "body": r.text[:800]}
            data = r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

    rows = data.get("value") or []
    out = []
    for item in (rows if isinstance(rows, list) else [rows]):
        if isinstance(item, dict):
            out.append({
                "station_code": item.get("StationCode") or item.get("Station_id") or item.get("Code"),
                "station": item.get("Station") or item.get("StationName"),
                "crowd_level": item.get("CrowdLevel") or item.get("Crowd") or item.get("Load"),
                "last_update": item.get("LastUpdate") or item.get("AsAt") or item.get("Timestamp"),
            })
        elif isinstance(item, str):
            out.append({"station_code": None, "station": None, "crowd_level": item, "last_update": None})
    return {"ok": True, "source":"LTA Datamall", "line": line, "updated_at": now_utc_iso(), "stations": out}

async def get_mrt_crowd_forecast(line: str):
    url = f"{LTA_API_BASE}/PCDForecast"
    headers = {"AccountKey": LTA_API_KEY, "accept": "application/json"}
    params = {"TrainLine": line}
    try:
        async with get_client(headers=headers, params=params) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return {"ok": False, "status": r.status_code, "body": r.text[:800]}
            data = r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

    rows = data.get("value") or []
    out = []
    for item in (rows if isinstance(rows, list) else [rows]):
        if isinstance(item, dict):
            out.append({
                "station_code": item.get("StationCode"),
                "station": item.get("Station") or item.get("StationName"),
                "time_slot": item.get("TimeSlot") or item.get("Time") or item.get("DateTime"),
                "crowd_level": item.get("CrowdLevel") or item.get("Crowd"),
            })
        elif isinstance(item, str):
            out.append({"station_code": None, "station": None, "time_slot": None, "crowd_level": item})
    return {"ok": True, "source":"LTA Datamall", "line": line, "updated_at": now_utc_iso(), "forecast": out}

# -------- Buses --------
def parse_eta_iso(s: Optional[str]):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None

def minutes_from_now(when):
    if not when:
        return None
    now = datetime.now(when.tzinfo or timezone.utc)
    delta = (when - now).total_seconds()
    if delta < 0:
        return 0
    return math.floor(delta / 60)

def norm_bus(bus: Dict[str, Any]) -> Dict[str, Any]:
    eta = parse_eta_iso(bus.get("EstimatedArrival"))
    return {
        "origin_code": bus.get("OriginCode"),
        "destination_code": bus.get("DestinationCode"),
        "estimated_arrival": bus.get("EstimatedArrival"),
        "eta_min": minutes_from_now(eta),
        "monitored": bus.get("Monitored"),
        "load": bus.get("Load"),
        "feature": bus.get("Feature"),
        "type": bus.get("Type"),
        "lat": bus.get("Latitude"),
        "lng": bus.get("Longitude"),
        "visit_number": bus.get("VisitNumber"),
    }

async def get_bus_arrivals(stop: str, service: Optional[str] = None):
    if not LTA_API_KEY:
        return {"ok": False, "error": "missing_key", "detail": "Set LTA_API_KEY in backend/.env"}

    url = f"{LTA_API_BASE}/v3/BusArrival"
    headers = {"AccountKey": LTA_API_KEY, "accept": "application/json"}
    params = {"BusStopCode": stop}
    if service:
        params["ServiceNo"] = service

    try:
        async with get_client(headers=headers) as client:
            r = await client.get(url, params=params)
            if r.status_code != 200:
                return {"ok": False, "status": r.status_code, "body": r.text[:800]}
            data = r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

    services = data.get("Services") or []
    out: List[Dict[str, Any]] = []
    for s in services:
        row = {
            "service_no": s.get("ServiceNo"),
            "operator": s.get("Operator"),
            "next": norm_bus(s.get("NextBus") or {}),
            "next2": norm_bus(s.get("NextBus2") or {}),
            "next3": norm_bus(s.get("NextBus3") or {}),
        }
        out.append(row)

    return {"ok": True, "bus_stop_code": data.get("BusStopCode") or stop, "updated_at": now_utc_iso(), "services": out}
