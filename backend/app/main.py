"""FastAPI application entry point, middleware, router registration, and static files."""
import os
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api import registration, patient, queue, token, public_display, device, auth, zones
from app.core.config import settings

# In production or when disabled, turn off interactive OpenAPI documentation
docs_url = "/docs" if settings.DOCS_ENABLED and settings.ENVIRONMENT != "production" else None
redoc_url = "/redoc" if settings.DOCS_ENABLED and settings.ENVIRONMENT != "production" else None

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="SmartQueue central API — Patient Queue & Crowd Management System",
    docs_url=docs_url,
    redoc_url=redoc_url,
)

# ── Rate Limiting ─────────────────────────────────────────────────────────────
limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.RATE_LIMIT_ENABLED and settings.ENVIRONMENT != "test",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── Security Headers & Request Correlation ID Middleware ───────────────────────
@app.middleware("http")
async def security_and_request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# ── CORS Middleware ───────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routers ───────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(registration.router, prefix="/api/v1/registrations", tags=["Registration"])
app.include_router(patient.router, prefix="/api/v1", tags=["Patient"])
app.include_router(queue.router, prefix="/api/v1/queues", tags=["Queue"])
app.include_router(token.router, prefix="/api/v1/tokens", tags=["Token Actions"])
app.include_router(zones.router, prefix="/api/v1/zones", tags=["Crowd & Zones"])
app.include_router(public_display.router, prefix="/api/v1/public", tags=["Public Display"])
app.include_router(device.router, prefix="/api/v1/devices", tags=["Device Ingestion"])

# ── Static File Mounts ────────────────────────────────────────────────────────
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
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
    }

@app.get("/", tags=["System"])
def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "docs": "/docs" if docs_url else "disabled",
        "health": "/health",
        "patient_app": "/patient/",
        "staff_app": "/staff/",
        "public_display": "/staff/public.html",
    }
