"""
app/main.py

FastAPI application entry point.
Owns: application creation, router registration, health endpoint, static file mount.
No business logic here. Doc A §5.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api import registration, patient, queue, public_display, device

import os

# ── Application ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "SmartQueue — Smart Patient Queue & Crowd Management System. "
        "Central backend for patient registration, queue management, "
        "and physical occupancy monitoring."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Permissive for development. In production, restrict to known frontend origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routers ───────────────────────────────────────────────────────────────
# Exact paths from Document A §2.
app.include_router(
    registration.router,
    prefix="/api/v1/registrations",
    tags=["Registration"],
)
app.include_router(
    patient.router,
    prefix="/api/v1",
    tags=["Patient"],
)
app.include_router(
    queue.router,
    prefix="/api/v1/queues",
    tags=["Queue"],
)
# Token sub-routes need a separate prefix to match /api/v1/tokens/{token_id}/...
app.include_router(
    queue.router,
    prefix="/api/v1",
    tags=["Token Actions"],
    include_in_schema=False,  # Avoid duplicate docs; real token routes defined in queue.py
)
app.include_router(
    public_display.router,
    prefix="/api/v1/public",
    tags=["Public Display"],
)
app.include_router(
    device.router,
    prefix="/api/v1/devices",
    tags=["Device (Deferred)"],
)

# ── Static files — patient frontend ──────────────────────────────────────────
# Served at /patient/ during development. In production the patient frontend
# can be hosted independently; just change PATIENT_FRONTEND_URL in .env.
_patient_frontend_path = os.path.join(
    os.path.dirname(__file__), "..", "..", "frontend-patient"
)
if os.path.isdir(_patient_frontend_path):
    app.mount(
        "/patient",
        StaticFiles(directory=_patient_frontend_path, html=True),
        name="patient-frontend",
    )


# ── Health endpoint ────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
def health():
    """Simple health check. Returns 200 when the server is running."""
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "app": settings.APP_NAME,
    }


# ── Root ──────────────────────────────────────────────────────────────────────
@app.get("/", tags=["System"])
def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "docs": "/docs",
        "health": "/health",
        "patient_app": "/patient/",
    }
