from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .core.config import ALLOWED_ORIGINS, PORT
from .api.routers import health, weather, mrt, bus
from datetime import datetime, timezone

app = FastAPI(title="Smart Travel Companion API", version="0.2.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# Global exception handler
@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    print(f"[{now_utc_iso()}] UNHANDLED ERROR: {exc!r}", flush=True)
    return JSONResponse(status_code=500, content={"ok": False, "error": "internal_server_error", "detail": str(exc)})

# Root + routes index
@app.get("/")
async def root():
    return {"ok": True, "project": "smart-travel", "version": "0.2.0"}

@app.get("/routes")
async def routes():
    return sorted([r.path for r in app.router.routes])

# Mount routers
app.include_router(health.router)
app.include_router(weather.router)
app.include_router(mrt.router)
app.include_router(bus.router)

# Entrypoint
if __name__ == "__main__":
    import uvicorn
    print(f"[{now_utc_iso()}] Starting Uvicorn...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True)
