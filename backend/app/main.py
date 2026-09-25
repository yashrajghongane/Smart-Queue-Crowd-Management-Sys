"""FastAPI application entry point and router/static-file registration."""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api import registration, patient, queue, token, public_display, device
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="SmartQueue central API",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(registration.router, prefix="/api/v1/registrations", tags=["Registration"])
app.include_router(patient.router, prefix="/api/v1", tags=["Patient"])
app.include_router(queue.router, prefix="/api/v1/queues", tags=["Queue"])
app.include_router(token.router, prefix="/api/v1/tokens", tags=["Token Actions"])
app.include_router(public_display.router, prefix="/api/v1/public", tags=["Public Display"])
app.include_router(device.router, prefix="/api/v1/devices", tags=["Device (Deferred)"])

_backend_parent = os.path.join(os.path.dirname(__file__), "..", "..")
_patient_frontend = os.path.join(_backend_parent, "frontend-patient")
_staff_frontend = os.path.join(_backend_parent, "frontend-staff")

if os.path.isdir(_patient_frontend):
    app.mount("/patient", StaticFiles(directory=_patient_frontend, html=True), name="patient-frontend")
if os.path.isdir(_staff_frontend):
    app.mount("/staff", StaticFiles(directory=_staff_frontend, html=True), name="staff-frontend")

@app.get("/public", include_in_schema=False)
@app.get("/display", include_in_schema=False)
def public_display_redirect():
    return RedirectResponse(url="/staff/public.html")

@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "version": settings.APP_VERSION, "app": settings.APP_NAME}

@app.get("/", tags=["System"])
def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "docs": "/docs",
        "health": "/health",
        "patient_app": "/patient/",
        "staff_app": "/staff/",
        "public_display": "/staff/public.html",
    }
