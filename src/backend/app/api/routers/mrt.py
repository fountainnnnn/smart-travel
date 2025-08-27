from fastapi import APIRouter, Query
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from ...services.lta import SUPPORTED_LINES, get_mrt_alerts, get_mrt_crowd

router = APIRouter()

# ------------------------
# Helpers
# ------------------------

def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _top_pinch_points(stations: List[Dict[str, Any]], k: int = 3) -> List[str]:
    pts = sorted(
        [s for s in stations if isinstance(s.get("crowd_score"), (int, float))],
        key=lambda s: s["crowd_score"],
        reverse=True,
    )
    names: List[str] = []
    for s in pts[:k]:
        code = s.get("station_code")
        name = s.get("station")
        names.append(code or name or "Unknown")
    return names

def _crowd_counts(stations: List[Dict[str, Any]]) -> Dict[str, int]:
    c = {"Low": 0, "Medium": 0, "High": 0, "Unknown": 0}
    for s in stations:
        lvl = (s.get("crowd_level") or "Unknown").title()
        if lvl not in c:
            lvl = "Unknown"
        c[lvl] += 1
    return c

def _code_num(code: str) -> Tuple[str, int]:
    """
    Split a station code into (alpha_prefix, numeric_suffix_as_int).
    If the numeric part is missing, returns a very large number for ordering.
    """
    c = (code or "").upper().strip()
    prefix = "".join([ch for ch in c if ch.isalpha()])[:2]
    try:
        num = int("".join([ch for ch in c if ch.isdigit()]))
    except Exception:
        num = 10_000_000
    return prefix, num

# Accept friendly names and map to canonical short codes
_ALIASES = {
    # Downtown Line
    "DOWNTOWN": "DTL", "DOWNTOWN LINE": "DTL", "DT": "DTL", "DTL": "DTL",
    # North South Line
    "NORTH SOUTH": "NSL", "NORTH SOUTH LINE": "NSL", "NS": "NSL", "NSL": "NSL",
    # East West Line
    "EAST WEST": "EWL", "EAST WEST LINE": "EWL", "EW": "EWL", "EWL": "EWL",
    # Circle Line (+ Extension)
    "CIRCLE": "CCL", "CIRCLE LINE": "CCL", "CC": "CCL", "CCL": "CCL",
    "CIRCLE LINE EXTENSION": "CEL", "CEL": "CEL", "CE": "CEL",
    # Thomson-East Coast Line
    "THOMSON EAST COAST": "TEL", "THOMSON-EAST COAST": "TEL",
    "TEL": "TEL", "TE": "TEL",
    # North East Line
    "NORTH EAST": "NEL", "NORTH EAST LINE": "NEL", "NE": "NEL", "NEL": "NEL",
    # LRTs / Branches
    "BUKIT PANJANG LRT": "BPL", "BPL": "BPL", "BP": "BPL",
    "SENGKANG LRT": "SLRT", "SLRT": "SLRT", "SE": "SLRT", "SW": "SLRT",
    "PUNGGOL LRT": "PLRT", "PLRT": "PLRT", "PE": "PLRT", "PW": "PLRT",
    "CHANGI AIRPORT BRANCH": "CGL", "CGL": "CGL", "CG": "CGL",
}

def _normalize_line(value: str) -> str:
    key = (value or "").upper().strip().replace("-", " ")
    return _ALIASES.get(key, key)

# ------------------------
# Routes
# ------------------------

@router.get("/mrt")
async def mrt_alerts():
    """
    Returns disruptions only (empty 'alerts' list when all clear).
    """
    return await get_mrt_alerts()

@router.get("/mrt/crowd")
async def mrt_crowd(
    line: str = Query("NSL", min_length=2, max_length=8),
):
    """
    Realtime crowd levels for a line (Low/Medium/High + numeric score),
    sorted in line order. Accepts friendly names, e.g. 'downtown', 'east west'.
    """
    line = _normalize_line(line)
    if line not in SUPPORTED_LINES:
        return {"ok": False, "error": "invalid_line", "normalized": line, "supported": sorted(SUPPORTED_LINES)}
    return await get_mrt_crowd(line)

@router.get("/mrt/crowd-forecast")
async def mrt_crowd_forecast(
    line: str = Query("NSL", min_length=2, max_length=8),
):
    """
    Forecast crowd levels for a line. If the upstream is rate-limited,
    the service returns the latest cached (stale) data when available.
    """
    from ...services.lta import get_mrt_crowd_forecast  # local import to avoid unused import elsewhere
    line = _normalize_line(line)
    if line not in SUPPORTED_LINES:
        return {"ok": False, "error": "invalid_line", "normalized": line, "supported": sorted(SUPPORTED_LINES)}
    return await get_mrt_crowd_forecast(line)

@router.get("/mrt/summary")
async def mrt_summary(
    line: str = Query("NSL", min_length=2, max_length=8),
    k: int = Query(3, ge=1, le=6, description="How many pinch points to return"),
    from_station: Optional[str] = Query(None, description="Start station code, e.g., NS14"),
    to_station: Optional[str] = Query(None, description="End station code, e.g., NS22"),
):
    """
    Fused view:
    - Alerts (disruptions only; empty if all clear)
    - Realtime crowd snapshot (ordered along the line; optionally filtered to a segment)
    - One-sentence summary + top-k pinch points
    """
    line = _normalize_line(line)
    if line not in SUPPORTED_LINES:
        return {"ok": False, "error": "invalid_line", "normalized": line, "supported": sorted(SUPPORTED_LINES)}

    alerts_res = await get_mrt_alerts()
    crowd_res = await get_mrt_crowd(line)

    if not (alerts_res.get("ok") and crowd_res.get("ok")):
        return {
            "ok": False,
            "error": "upstream_error",
            "alerts_ok": alerts_res.get("ok"),
            "crowd_ok": crowd_res.get("ok"),
            "line": line,
            "updated_at": _now_utc_iso(),
        }

    stations = crowd_res.get("stations") or []

    # Optional segment filter
    if from_station and to_station:
        p1, n1 = _code_num(from_station)
        p2, n2 = _code_num(to_station)
        if p1 == p2 and p1:
            lo, hi = (n1, n2) if n1 <= n2 else (n2, n1)
            stations = [
                s for s in stations
                if isinstance(s.get("station_code"), str)
                and _code_num(s["station_code"])[0] == p1
                and lo <= _code_num(s["station_code"])[1] <= hi
            ]

    counts = _crowd_counts(stations)
    pinch = _top_pinch_points(stations, k=k)
    max_score = max([s.get("crowd_score") or 0.0 for s in stations] or [0.0])

    # Disruptions already filtered in services.lta to only real issues
    disruptions = [{
        "line": a.get("line"),
        "status": a.get("status"),
        "message": a.get("message"),
        "timestamp": a.get("timestamp"),
        "stations": a.get("stations"),
        "bus_shuttle": a.get("bus_shuttle"),
    } for a in (alerts_res.get("alerts") or [])]
    has_disruption = bool(disruptions)

    # Build summary sentence
    parts = []
    total = sum(counts.values())
    if total > 0:
        majority = max(counts, key=lambda k2: counts[k2])
        scope = f" {from_station}→{to_station}" if (from_station and to_station) else ""
        parts.append(f"{line}{scope} mostly {majority}")
        if pinch:
            parts.append(f"pinch at {', '.join(pinch)}")
    else:
        parts.append(f"{line} crowd data unavailable")

    parts.append("service alert active" if has_disruption else "no service alerts")
    summary = ". ".join(parts) + "."

    return {
        "ok": True,
        "line": line,
        "updated_at": crowd_res.get("updated_at") or _now_utc_iso(),
        "age_sec": crowd_res.get("age_sec", 0),
        "alerts_age_sec": alerts_res.get("age_sec", 0),
        "summary": summary,
        "pinch_points": pinch,
        "max_crowd_score": round(max_score, 2),
        "counts": counts,
        "has_disruption": has_disruption,
        "disruptions": disruptions,
        "segment": {"from": from_station, "to": to_station} if (from_station and to_station) else None,
        "sources": {
            "alerts": alerts_res.get("source"),
            "crowd": crowd_res.get("source"),
        },
    }
