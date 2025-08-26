from typing import Optional
from fastapi import APIRouter, Query
from ...services.lta import get_bus_arrivals

router = APIRouter()

@router.get("/bus/arrivals")
async def bus_arrivals(stop: str = Query(..., description="BusStopCode"), service: Optional[str] = None):
    return await get_bus_arrivals(stop=stop, service=service)
