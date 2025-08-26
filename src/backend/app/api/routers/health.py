from fastapi import APIRouter
from datetime import datetime, timezone
from ...schemas.common import HealthOut
from ...core.config import cfg_summary

router = APIRouter()

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

@router.get("/health", response_model=HealthOut)
async def health():
    return HealthOut(status="ok", time_utc=now_utc_iso())

@router.get("/config")
async def config():
    return cfg_summary()
