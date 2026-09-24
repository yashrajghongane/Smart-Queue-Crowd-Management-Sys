"""
app/schemas/schemas.py

Pydantic request/response models — exact API contract from Document A §2.
No business logic here: only validation and serialisation shapes.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator
import re


# ── Common ────────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """Generic error response."""
    detail: str


# ── Registration ──────────────────────────────────────────────────────────────
# Doc A §2.1 and §2.2

class RegistrationRequest(BaseModel):
    """
    Shared request body for QR and staff-assisted registration.
    The registration source (QR vs STAFF) is determined by the endpoint, not the body.
    """
    full_name: str = Field(..., min_length=1, max_length=150)
    mobile: str = Field(..., min_length=7, max_length=15)
    department_id: str = Field(..., description="UUID of the target department")

    @field_validator("mobile")
    @classmethod
    def mobile_digits_only(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if len(digits) < 7:
            raise ValueError("mobile must contain at least 7 digits")
        # Normalize common prefixes (+91 or leading 0) for 10-digit mobile numbers
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        elif len(digits) == 11 and digits.startswith("0"):
            digits = digits[1:]
        return digits  # Store normalised digits

    @field_validator("full_name")
    @classmethod
    def full_name_strip(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("full_name must not be empty or whitespace only")
        return stripped


class RegistrationResponse(BaseModel):
    """Successful registration — Doc A §2.1 response 201."""
    patient_id: str
    visit_id: str
    token_id: str
    token_number: str
    state: str
    department_id: str


class DuplicateActiveVisitResponse(BaseModel):
    """Duplicate active registration — Doc A §2.1 response 409."""
    error: str = "ACTIVE_VISIT_EXISTS"
    message: str = "An active visit already exists for this patient and department."
    visit_id: str
    token_id: str
    token_number: str


# ── Patient status ────────────────────────────────────────────────────────────
# Doc A §2.9

class PatientStatusResponse(BaseModel):
    """Patient token/queue status — Doc A §2.9 response 200."""
    visit_id: str
    token_number: str
    state: str
    patients_ahead: int
    serving_token: Optional[str]  # token_number of the currently SERVING token, or null
    department_id: str
    updated_at: datetime


# ── Queue summary ─────────────────────────────────────────────────────────────
# Doc A §2.3

class QueueSummaryResponse(BaseModel):
    """Queue summary for staff dashboard — Doc A §2.3 response 200."""
    queue_id: str
    department_id: str
    waiting_count: int
    serving_token: Optional[str]
    serving_token_id: Optional[str]
    updated_at: datetime


# ── Queue actions ─────────────────────────────────────────────────────────────
# Doc A §2.4 — Call next

class CallNextResponse(BaseModel):
    token_id: str
    token_number: str
    previous_state: str
    state: str
    called_at: datetime


class NoWaitingTokensResponse(BaseModel):
    error: str = "NO_WAITING_TOKENS"
    message: str = "No eligible waiting token is available."


# Doc A §2.5 — Hold

class HoldRequest(BaseModel):
    reason: Optional[str] = None


class TokenStateChangeResponse(BaseModel):
    token_id: str
    previous_state: str
    state: str


# Doc A §2.6 — Recall (empty request body)

class RecallRequest(BaseModel):
    pass


# Doc A §2.7 — Skip

class SkipRequest(BaseModel):
    reason: Optional[str] = None


# Doc A §2.8 — Complete (empty request body)

class CompleteRequest(BaseModel):
    pass


class CompleteResponse(BaseModel):
    token_id: str
    previous_state: str
    state: str
    completed_at: datetime


# ── Zone occupancy ────────────────────────────────────────────────────────────
# Doc A §2.10

class ZoneOccupancyResponse(BaseModel):
    zone_id: str
    occupancy: int
    capacity: int
    capacity_alert: str
    updated_at: datetime


# ── Public display ────────────────────────────────────────────────────────────
# Doc A §2.10 (second section — public display)

class PublicDisplayResponse(BaseModel):
    queue_id: str
    serving_token: Optional[str]
    next_token: Optional[str]
    waiting_count: int
    updated_at: datetime


# ── Device event ──────────────────────────────────────────────────────────────
# Doc A §2.11 — ESP32 event ingestion (deferred to hardware milestone)

class DeviceEventRequest(BaseModel):
    device_id: str
    zone_id: str
    sequence: int
    event_type: str = Field(..., pattern="^(ENTRY|EXIT)$")
    event_at: datetime
    firmware_version: str


class DeviceEventResponse(BaseModel):
    device_id: str
    zone_id: str
    sequence: int
    accepted: bool
    event_type: str
    occupancy: int
    capacity_alert: str
    processed_at: datetime
