"""Pydantic request/response models matching Document A."""
from __future__ import annotations
from datetime import datetime
from typing import Optional
import re
from pydantic import BaseModel, Field, field_validator

class ErrorResponse(BaseModel):
    detail: str

class RegistrationRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=150)
    mobile: str = Field(..., min_length=7, max_length=15)
    department_id: str = Field(..., description="UUID of the target department")

    @field_validator("mobile")
    @classmethod
    def mobile_digits_only(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if len(digits) < 7:
            raise ValueError("mobile must contain at least 7 digits")
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        elif len(digits) == 11 and digits.startswith("0"):
            digits = digits[1:]
        return digits

    @field_validator("full_name")
    @classmethod
    def full_name_strip(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("full_name must not be empty or whitespace only")
        return stripped

class RegistrationResponse(BaseModel):
    patient_id: str
    visit_id: str
    token_id: str
    token_number: str
    state: str
    department_id: str

class DuplicateActiveVisitResponse(BaseModel):
    error: str = "ACTIVE_VISIT_EXISTS"
    message: str = "An active visit already exists for this patient and department."
    visit_id: str
    token_id: str
    token_number: str

class PatientStatusResponse(BaseModel):
    visit_id: str
    token_number: str
    state: str
    patients_ahead: int
    serving_token: Optional[str]
    department_id: str
    updated_at: datetime

class QueueSummaryResponse(BaseModel):
    queue_id: str
    department_id: str
    waiting_count: int
    serving_token: Optional[str]
    serving_token_id: Optional[str]
    updated_at: datetime

class CallNextResponse(BaseModel):
    token_id: str
    token_number: str
    previous_state: str
    state: str
    called_at: datetime

class NoWaitingTokensResponse(BaseModel):
    error: str = "NO_WAITING_TOKENS"
    message: str = "No eligible waiting token is available."

class HoldRequest(BaseModel):
    reason: Optional[str] = None

class TokenStateChangeResponse(BaseModel):
    token_id: str
    previous_state: str
    state: str

class RecallRequest(BaseModel):
    pass

class SkipRequest(BaseModel):
    reason: Optional[str] = None

class CompleteRequest(BaseModel):
    pass

class CompleteResponse(BaseModel):
    token_id: str
    previous_state: str
    state: str
    completed_at: datetime

class ZoneOccupancyResponse(BaseModel):
    zone_id: str
    occupancy: int
    capacity: int
    capacity_alert: str
    updated_at: datetime

class PublicDisplayResponse(BaseModel):
    queue_id: str
    serving_token: Optional[str]
    next_token: Optional[str]
    waiting_count: int
    updated_at: datetime

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
