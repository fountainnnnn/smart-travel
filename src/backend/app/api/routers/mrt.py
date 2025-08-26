from fastapi import APIRouter, Query
from ...services.lta import SUPPORTED_LINES, get_mrt_alerts, get_mrt_crowd, get_mrt_crowd_forecast

router = APIRouter()

@router.get("/mrt")
async def mrt_alerts():
    return await get_mrt_alerts()

@router.get("/mrt/crowd")
async def mrt_crowd(line: str = Query("NSL", min_length=2, max_length=5)):
    line = line.upper().strip()
    if line not in SUPPORTED_LINES:
        return {"ok": False, "error": "invalid_line", "supported": sorted(SUPPORTED_LINES)}
    return await get_mrt_crowd(line)

@router.get("/mrt/crowd-forecast")
async def mrt_crowd_forecast(line: str = Query("NSL", min_length=2, max_length=5)):
    line = line.upper().strip()
    if line not in SUPPORTED_LINES:
        return {"ok": False, "error": "invalid_line", "supported": sorted(SUPPORTED_LINES)}
    return await get_mrt_crowd_forecast(line)
