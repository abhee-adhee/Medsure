from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging

from backend.app.config import STATIC_DIR, BASE_DIR
from backend.app.db import engine, Base
from backend.app.routes import scan, scans, serial, batch, alerts, receiving, stats

logger = logging.getLogger("medsure")

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MedSure Vision API",
    description="Backend API for MedSure Vision screening platform",
    version="1.0.0"
)

# CORS configuration allowing frontend at localhost:5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for heatmaps and assets
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include Routers
app.include_router(scan.router)
app.include_router(scans.router)
app.include_router(serial.router)
app.include_router(batch.router)
app.include_router(alerts.router)
app.include_router(receiving.router)
app.include_router(stats.router)


@app.get("/", tags=["UI"])
async def root():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "service": "MedSure Vision API",
        "status": "ok",
        "docs": "/docs",
    }


# Global exception handler enforcing contract error format
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred.",
            "error_code": "INTERNAL_SERVER_ERROR",
            "status": 500
        }
    )
