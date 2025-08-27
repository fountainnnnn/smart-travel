from typing import Dict, Any, List, Optional, Callable, Tuple
from datetime import datetime, timezone, timedelta
import math
from ..core.config import LTA_API_BASE, LTA_API_KEY
from ..core.http import get_client

# Try to use IANA tz; fallback to fixed +08:00 if not available
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
    SGT_TZ = ZoneInfo("Asia/Singapore")
except Exception:
    SGT_TZ = timezone(timedelta(hours=8))

# =========================
# Helpers
# =========================

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s or not isinstance(s, str):
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None

def _to_sgt_iso_from_str(s: Optional[str]) -> Optional[str]:
    dt = _parse_iso(s)
    if not dt:
        return None
    try:
        return dt.astimezone(SGT_TZ).isoformat()
    except Exception:
        return None

def normalize_status(val) -> str:
    if isinstance(val, str):
        s = val.strip()
        return s if s else "Unknown"
    try:
        n = int(val)
    except Exception:
        return str(val)
    # LTA sometimes uses numeric codes in some feeds
    return {
        0: "No Service Alert",
        1: "No Service Alert",
        2: "Minor Disruption",
        3: "Major Disruption"
    }.get(n, str(n))

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

def parse_eta_iso(s: Optional[str]):
    # kept for bus ETA parsing
    return _parse_iso(s)

def minutes_from_now(when):
    if not when:
        return None
    now = datetime.now(when.tzinfo or timezone.utc)
    delta = (when - now).total_seconds()
    if delta < 0:
        return 0
    return math.floor(delta / 60)

# =========================
# Constants and mappings
# =========================

# Short codes used widely in SG
LINE_MAP_FULL_TO_SHORT: Dict[str, str] = {
    "North South Line": "NSL",
    "East West Line": "EWL",
    "Downtown Line": "DTL",
    "Circle Line": "CCL",
    "Thomson-East Coast Line": "TEL",
    "North East Line": "NEL",
    "Bukit Panjang LRT": "BPL",
    "Sengkang LRT": "SLRT",
    "Punggol LRT": "PLRT",
    "Changi Airport Branch": "CGL",
    "Circle Line Extension": "CEL",
}

# For sorting along a line (prefix priority)
LINE_PREFIXES: Dict[str, Tuple[str, ...]] = {
    "DTL": ("DT",),
    "NSL": ("NS",),
    "EWL": ("EW", "CG"),   # Changi branch shares EW system
    "CCL": ("CC", "CE"),   # Circle extension
    "NEL": ("NE",),
    "TEL": ("TE",),
    "BPL": ("BP",),
    "SLRT": ("SE", "SW"),  # Sengkang East/West loops
    "PLRT": ("PE", "PW"),  # Punggol East/West loops
    "CGL": ("CG",),
    "CEL": ("CE",),
}

SUPPORTED_LINES = {
    "CCL","CEL","CGL","DTL","EWL","NEL","NSL","BPL","SLRT","PLRT","TEL"
}

LEVEL_TEXT_MAP = {"l": "Low", "m": "Medium", "h": "High"}
LEVEL_SCORE_MAP = {"l": 0.25, "m": 0.60, "h": 0.90}

def _infer_station_code_from_name(name: Optional[str]) -> Optional[str]:
    """
    If StationCode is missing but Station name looks like 'DT14' or 'NS1', use it.
    """
    if not isinstance(name, str):
        return None
    s = name.strip().upper()
    # typical codes: 2 letters + number(s), sometimes branch like 'CG2'
    if len(s) <= 5 and any(c.isdigit() for c in s) and s[:2].isalpha():
        return s
    return None

def _station_rank(line: str, code_or_name: Optional[str]) -> Tuple[int, int, str]:
    """
    Return a tuple for sorting stations along the specified line:
    (prefix_index, numeric_index, original_string)
    Unknowns go to the end.
    """
    if not isinstance(code_or_name, str):
        return (99, 10_000_000, "")
    s = code_or_name.strip().upper()
    prefixes = LINE_PREFIXES.get(line, ())
    # find a matching prefix at the start
    for idx, p in enumerate(prefixes):
        if s.startswith(p):
            # extract the integer part following the prefix
            num_str = s[len(p):]
            try:
                n = int("".join(ch for ch in num_str if ch.isdigit()))
            except Exception:
                n = 10_000_000
            return (idx, n, s)
    # fallback: try 2-letter + number generic
    if len(s) >= 3 and s[:2].isalpha():
        try:
            n = int("".join(ch for ch in s[2:] if ch.isdigit()))
        except Exception:
            n = 10_000_000
        return (98, n, s)
    return (99, 10_000_000, s)

# =========================
# Tiny in-memory TTL cache
# =========================

_CACHE: Dict[str, Tuple[datetime, Any]] = {}
CACHE_TTL = timedelta(seconds=90)

def cache_get(key: str):
    item = _CACHE.get(key)
    if not item:
        return None
    ts, val = item
    if datetime.now(timezone.utc) - ts < CACHE_TTL:
        return val
    _CACHE.pop(key, None)
    return None

def cache_set(key: str, val: Any):
    _CACHE[key] = (datetime.now(timezone.utc), val)

async def _cached(key: str, fetcher: Callable[[], Any]) -> Any:
    """
    Simple cache with freshness; when returning a cached dict, refresh `age_sec`
    and ensure `updated_local` is present based on its `updated_at` if present.
    """
    hit = cache_get(key)
    if hit is not None:
        if isinstance(hit, dict):
            resp = dict(hit)  # shallow copy
            ua = resp.get("updated_at")
            dt = _parse_iso(ua) if isinstance(ua, str) else None
            if dt:
                now = datetime.now(timezone.utc)
                resp["age_sec"] = max(0, int((now - dt).total_seconds()))
                resp["updated_local"] = dt.astimezone(SGT_TZ).isoformat()
            return resp
        return hit

    val = await fetcher()
    # Only cache if the call succeeded
    if isinstance(val, dict) and val.get("ok"):
        # attach age_sec and updated_local before caching
        ua = val.get("updated_at") if isinstance(val.get("updated_at"), str) else None
        dt = _parse_iso(ua) if ua else None
        if dt is not None:
            now = datetime.now(timezone.utc)
            val = dict(val)
            val["age_sec"] = max(0, int((now - dt).total_seconds()))
            val["updated_local"] = dt.astimezone(SGT_TZ).isoformat()
        cache_set(key, val)
    return val

# =========================
# MRT alerts
# =========================

async def get_mrt_alerts():
    if not LTA_API_KEY:
        # Keep a clear message if key missing
        updated = now_utc_iso()
        return {
            "ok": True,
            "source": "LTA Datamall",
            "updated_at": updated,
            "updated_local": _to_sgt_iso_from_str(updated),
            "age_sec": 0,
            "has_disruption": False,
            "alerts": [{
                "line": "ALL",
                "status": "MissingKey",
                "message": "Set LTA_API_KEY in backend/.env",
                "timestamp": None,
                "direction": None,
                "stations": None,
                "bus_shuttle": None
            }]
        }

    async def _fetch():
        url = f"{LTA_API_BASE}/TrainServiceAlerts"
        headers = {"AccountKey": LTA_API_KEY, "accept": "application/json"}

        try:
            async with get_client(headers=headers) as client:
                r = await client.get(url)
                if r.status_code != 200:
                    updated = now_utc_iso()
                    return {
                        "ok": False,
                        "source": "LTA Datamall",
                        "updated_at": updated,
                        "updated_local": _to_sgt_iso_from_str(updated),
                        "age_sec": 0,
                        "error": {"status": r.status_code, "body": r.text[:800]},
                        "has_disruption": None,
                        "alerts": []
                    }
                data = r.json()
        except Exception as e:
            updated = now_utc_iso()
            return {
                "ok": False,
                "source": "LTA Datamall",
                "updated_at": updated,
                "updated_local": _to_sgt_iso_from_str(updated),
                "age_sec": 0,
                "error": {"exception": str(e)},
                "has_disruption": None,
                "alerts": []
            }

        raw = data.get("value")
        temp: List[Dict[str, Any]] = []

        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    temp.append({
                        "line": item.get("Line", "Unknown"),
                        "status": item.get("Status", "Unknown"),
                        "message": item.get("Message"),
                        "timestamp": item.get("CreatedDate"),
                        "direction": item.get("Direction"),
                        "stations": item.get("AffectedStations"),
                        "bus_shuttle": item.get("BusShuttle"),
                    })
                elif isinstance(item, str):
                    temp.append({
                        "line": "ALL",
                        "status": item,
                        "message": None,
                        "timestamp": None,
                        "direction": None,
                        "stations": None,
                        "bus_shuttle": None
                    })
        elif isinstance(raw, dict):
            temp.append({
                "line": raw.get("Line", "Unknown"),
                "status": raw.get("Status", "Unknown"),
                "message": raw.get("Message"),
                "timestamp": raw.get("CreatedDate"),
                "direction": raw.get("Direction"),
                "stations": raw.get("AffectedStations"),
                "bus_shuttle": raw.get("BusShuttle"),
            })
        elif isinstance(raw, str):
            temp.append({
                "line": "ALL",
                "status": raw,
                "message": None,
                "timestamp": None,
                "direction": None,
                "stations": None,
                "bus_shuttle": None
            })
        else:
            updated = now_utc_iso()
            return {
                "ok": False,
                "source": "LTA Datamall",
                "updated_at": updated,
                "updated_local": _to_sgt_iso_from_str(updated),
                "age_sec": 0,
                "error": {"reason": "unexpected_payload", "type": type(raw).__name__},
                "has_disruption": None,
                "alerts": [],
                "raw": data
            }

        # Normalize and map line names to short codes when possible
        normalized = []
        for a in temp:
            line_raw = a.get("line") or "Unknown"
            line_short = LINE_MAP_FULL_TO_SHORT.get(line_raw, line_raw)
            normalized.append({
                "line": line_short,
                "status": normalize_status(a.get("status")),
                "message": normalize_message(a.get("message")),
                "timestamp": a.get("timestamp"),
                "direction": a.get("direction"),
                "stations": a.get("stations"),
                "bus_shuttle": a.get("bus_shuttle"),
            })

        # Keep only real disruptions; hide "Unknown | No Service Alert" noise
        disruptive = [
            x for x in normalized
            if (x.get("status") or "").strip() not in ("No Service Alert", "Normal", "All Clear")
        ]
        has_disruption = bool(disruptive)

        updated = now_utc_iso()
        return {
            "ok": True,
            "source": "LTA Datamall",
            "updated_at": updated,
            "updated_local": _to_sgt_iso_from_str(updated),
            "age_sec": 0,  # treat as fresh at fetch time
            "has_disruption": has_disruption,
            "alerts": disruptive
        }

    return await _cached("mrt_alerts", _fetch)

# =========================
# MRT crowd realtime
# =========================

async def get_mrt_crowd(line: str):
    # Accept both full and short names, normalize to short if possible
    line = (line or "").strip()
    if line in LINE_MAP_FULL_TO_SHORT:
        norm_line = LINE_MAP_FULL_TO_SHORT[line]
    else:
        norm_line = line.upper()

    if not LTA_API_KEY:
        updated = now_utc_iso()
        return {
            "ok": False,
            "error": "missing_key",
            "detail": "Set LTA_API_KEY in backend/.env",
            "updated_at": updated,
            "updated_local": _to_sgt_iso_from_str(updated),
            "age_sec": 0,
        }

    async def _fetch():
        url = f"{LTA_API_BASE}/PCDRealTime"
        headers = {"AccountKey": LTA_API_KEY, "accept": "application/json"}
        params = {"TrainLine": norm_line}

        try:
            async with get_client(headers=headers, params=params) as client:
                r = await client.get(url)
                if r.status_code != 200:
                    updated_iso = now_utc_iso()
                    return {
                        "ok": False,
                        "status": r.status_code,
                        "body": r.text[:800],
                        "updated_at": updated_iso,
                        "updated_local": _to_sgt_iso_from_str(updated_iso),
                        "age_sec": 0,
                    }
                data = r.json()
        except Exception as e:
            updated_iso = now_utc_iso()
            return {
                "ok": False,
                "error": str(e),
                "updated_at": updated_iso,
                "updated_local": _to_sgt_iso_from_str(updated_iso),
                "age_sec": 0,
            }

        rows = data.get("value") or []
        out: List[Dict[str, Any]] = []
        iterable = rows if isinstance(rows, list) else [rows]

        now_iso = now_utc_iso()
        for item in iterable:
            if isinstance(item, dict):
                raw_level = item.get("CrowdLevel") or item.get("Crowd") or item.get("Load")
                raw_key = str(raw_level).strip().lower()[:1] if raw_level else None
                text = LEVEL_TEXT_MAP.get(raw_key, "Unknown")
                score = LEVEL_SCORE_MAP.get(raw_key, 0.0)
                last_update = item.get("LastUpdate") or item.get("AsAt") or item.get("Timestamp") or None

                name = item.get("Station") or item.get("StationName")
                code = item.get("StationCode") or item.get("Station_id") or item.get("Code")
                if not code:
                    code = _infer_station_code_from_name(name)

                out.append({
                    "station_code": code,
                    "station": name,
                    "crowd_level": text,
                    "crowd_score": score,
                    "raw_level": raw_level,  # keep original for debugging
                    "last_update": last_update or now_iso,
                })
            elif isinstance(item, str):
                k = item.strip().lower()[:1]
                out.append({
                    "station_code": None,
                    "station": None,
                    "crowd_level": LEVEL_TEXT_MAP.get(k, "Unknown"),
                    "crowd_score": LEVEL_SCORE_MAP.get(k, 0.0),
                    "raw_level": item,
                    "last_update": now_iso
                })

        # Sort stations along the line for better UX
        out.sort(key=lambda s: _station_rank(
            norm_line,
            (s.get("station_code") or s.get("station") or "")
        ))

        updated_iso = now_utc_iso()
        # age from the newest 'last_update' we saw; fall back to 0
        try:
            latest = max([_parse_iso(s["last_update"]) for s in out if s.get("last_update")] or [datetime.now(timezone.utc)])
            age = max(0, int((datetime.now(timezone.utc) - latest).total_seconds()))
        except Exception:
            age = 0

        return {
            "ok": True,
            "source": "LTA Datamall",
            "line": norm_line,
            "updated_at": updated_iso,
            "updated_local": _to_sgt_iso_from_str(updated_iso),
            "age_sec": age,
            "stations": out
        }

    return await _cached(f"pcd_realtime:{norm_line}", _fetch)

# =========================
# MRT crowd forecast (with stale fallback)
# =========================

async def get_mrt_crowd_forecast(line: str):
    # Normalize line name
    line = (line or "").strip()
    if line in LINE_MAP_FULL_TO_SHORT:
        norm_line = LINE_MAP_FULL_TO_SHORT[line]
    else:
        norm_line = line.upper()

    if not LTA_API_KEY:
        updated = now_utc_iso()
        return {
            "ok": False,
            "error": "missing_key",
            "detail": "Set LTA_API_KEY in backend/.env",
            "updated_at": updated,
            "updated_local": _to_sgt_iso_from_str(updated),
            "age_sec": 0,
        }

    cache_key = f"pcd_forecast:{norm_line}"

    async def _fetch():
        url = f"{LTA_API_BASE}/PCDForecast"
        headers = {"AccountKey": LTA_API_KEY, "accept": "application/json"}
        params = {"TrainLine": norm_line}

        try:
            async with get_client(headers=headers, params=params) as client:
                r = await client.get(url)
                if r.status_code != 200:
                    updated_iso = now_utc_iso()
                    return {
                        "ok": False,
                        "status": r.status_code,
                        "body": r.text[:800],
                        "updated_at": updated_iso,
                        "updated_local": _to_sgt_iso_from_str(updated_iso),
                        "age_sec": 0,
                    }
                data = r.json()
        except Exception as e:
            updated_iso = now_utc_iso()
            return {
                "ok": False,
                "error": str(e),
                "updated_at": updated_iso,
                "updated_local": _to_sgt_iso_from_str(updated_iso),
                "age_sec": 0,
            }

        rows = data.get("value") or []
        out: List[Dict[str, Any]] = []
        iterable = rows if isinstance(rows, list) else [rows]

        for item in iterable:
            if isinstance(item, dict):
                raw_level = item.get("CrowdLevel") or item.get("Crowd")
                raw_key = str(raw_level).strip().lower()[:1] if raw_level else None
                text = LEVEL_TEXT_MAP.get(raw_key, "Unknown")
                score = LEVEL_SCORE_MAP.get(raw_key, 0.0)
                out.append({
                    "station_code": item.get("StationCode"),
                    "station": item.get("Station") or item.get("StationName"),
                    "time_slot": item.get("TimeSlot") or item.get("Time") or item.get("DateTime"),
                    "crowd_level": text,
                    "crowd_score": score,
                    "raw_level": raw_level
                })
            elif isinstance(item, str):
                k = item.strip().lower()[:1]
                out.append({
                    "station_code": None,
                    "station": None,
                    "time_slot": None,
                    "crowd_level": LEVEL_TEXT_MAP.get(k, "Unknown"),
                    "crowd_score": LEVEL_SCORE_MAP.get(k, 0.0),
                    "raw_level": item
                })

        updated_iso = now_utc_iso()
        return {
            "ok": True,
            "source": "LTA Datamall",
            "line": norm_line,
            "updated_at": updated_iso,
            "updated_local": _to_sgt_iso_from_str(updated_iso),
            "age_sec": 0,  # treat as fresh at fetch time
            "forecast": out
        }

    res = await _cached(cache_key, _fetch)
    if not isinstance(res, dict):
        return res

    if not res.get("ok"):
        # stale fallback if available
        cached = cache_get(cache_key)
        if cached and isinstance(cached, dict):
            cached = dict(cached)
            cached["stale"] = True
            # compute/update age_sec and updated_local from cached updated_at if possible
            ua = cached.get("updated_at")
            dt = _parse_iso(ua) if isinstance(ua, str) else None
            if dt:
                now = datetime.now(timezone.utc)
                cached["age_sec"] = max(0, int((now - dt).total_seconds()))
                cached["updated_local"] = dt.astimezone(SGT_TZ).isoformat()
            return cached
    else:
        # ensure updated_local present for fresh result too
        if "updated_local" not in res and isinstance(res.get("updated_at"), str):
            res = dict(res)
            res["updated_local"] = _to_sgt_iso_from_str(res["updated_at"])
    return res

# =========================
# Buses
# =========================

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
        updated = now_utc_iso()
        return {
            "ok": False,
            "error": "missing_key",
            "detail": "Set LTA_API_KEY in backend/.env",
            "updated_at": updated,
            "updated_local": _to_sgt_iso_from_str(updated),
            "age_sec": 0,
        }

    async def _fetch():
        url = f"{LTA_API_BASE}/v3/BusArrival"
        headers = {"AccountKey": LTA_API_KEY, "accept": "application/json"}
        params = {"BusStopCode": stop}
        if service:
            params["ServiceNo"] = service

        try:
            async with get_client(headers=headers) as client:
                r = await client.get(url, params=params)
                if r.status_code != 200:
                    updated_at = now_utc_iso()
                    return {
                        "ok": False,
                        "status": r.status_code,
                        "body": r.text[:800],
                        "updated_at": updated_at,
                        "updated_local": _to_sgt_iso_from_str(updated_at),
                        "age_sec": 0,
                    }
                data = r.json()
        except Exception as e:
            updated_at = now_utc_iso()
            return {
                "ok": False,
                "error": str(e),
                "updated_at": updated_at,
                "updated_local": _to_sgt_iso_from_str(updated_at),
                "age_sec": 0,
            }

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

        updated_at = now_utc_iso()
        return {
            "ok": True,
            "bus_stop_code": data.get("BusStopCode") or stop,
            "updated_at": updated_at,
            "updated_local": _to_sgt_iso_from_str(updated_at),
            "age_sec": 0,
            "services": out
        }

    # Very short TTL cache for bus arrivals to soften bursts
    return await _cached(f"bus_arrivals:{stop}:{service or '_all_'}", _fetch)
