"""
app/models/models.py

SQLAlchemy ORM models — one class per table from Document A §3.
No business logic here: only column definitions and relationships.

UUIDs are stored as String(36) for SQLite/PostgreSQL portability.
All timestamps are UTC.
"""
import uuid
from datetime import datetime, date as date_type
from typing import Optional

from sqlalchemy import (
    String, Integer, Boolean, Date, DateTime,
    ForeignKey, UniqueConstraint, CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.repositories.database import Base


# ── Helpers ───────────────────────────────────────────────────────────────────

def _new_uuid() -> str:
    """Generate a new UUID4 as a hyphenated string."""
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    """Current UTC datetime (naive, stored as UTC in DB)."""
    return datetime.utcnow()


# ── Department ────────────────────────────────────────────────────────────────
# Doc A §3.1

class Department(Base):
    __tablename__ = "departments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    queues: Mapped[list["Queue"]] = relationship("Queue", back_populates="department")
    visits: Mapped[list["Visit"]] = relationship("Visit", back_populates="department")


# ── Queue ─────────────────────────────────────────────────────────────────────
# Doc A §3.2

class Queue(Base):
    __tablename__ = "queues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    department_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("departments.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    prefix: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    department: Mapped["Department"] = relationship("Department", back_populates="queues")
    tokens: Mapped[list["Token"]] = relationship("Token", back_populates="queue")
    visits: Mapped[list["Visit"]] = relationship("Visit", back_populates="queue")


# ── Patient ───────────────────────────────────────────────────────────────────
# Doc A §3.3

class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    mobile: Mapped[str] = mapped_column(String(15), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, onupdate=_utcnow
    )

    visits: Mapped[list["Visit"]] = relationship("Visit", back_populates="patient")


# ── Visit ─────────────────────────────────────────────────────────────────────
# Doc A §3.4

class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patients.id"), nullable=False
    )
    department_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("departments.id"), nullable=False
    )
    queue_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("queues.id"), nullable=False
    )
    registration_source: Mapped[str] = mapped_column(
        String(20), nullable=False  # "QR" or "STAFF"
    )
    visit_date: Mapped[date_type] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    patient: Mapped["Patient"] = relationship("Patient", back_populates="visits")
    department: Mapped["Department"] = relationship("Department", back_populates="visits")
    queue: Mapped["Queue"] = relationship("Queue", back_populates="visits")
    token: Mapped[Optional["Token"]] = relationship(
        "Token", back_populates="visit", uselist=False
    )

    __table_args__ = (
        CheckConstraint("registration_source IN ('QR', 'STAFF')", name="ck_visit_registration_source"),
    )


# ── Token ─────────────────────────────────────────────────────────────────────
# Doc A §3.5
# States: WAITING, SERVING, HOLD, SKIPPED, COMPLETED

_TOKEN_STATES = ("WAITING", "SERVING", "HOLD", "SKIPPED", "COMPLETED")


class Token(Base):
    __tablename__ = "tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    visit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("visits.id"), unique=True, nullable=False
    )
    queue_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("queues.id"), nullable=False
    )
    token_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="WAITING")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    called_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, onupdate=_utcnow
    )

    visit: Mapped["Visit"] = relationship("Visit", back_populates="token")
    queue: Mapped["Queue"] = relationship("Queue", back_populates="tokens")
    queue_events: Mapped[list["QueueEvent"]] = relationship(
        "QueueEvent", back_populates="token"
    )

    __table_args__ = (
        UniqueConstraint("queue_id", "sequence_number", name="uq_token_queue_sequence"),
        CheckConstraint(
            "state IN ('WAITING','SERVING','HOLD','SKIPPED','COMPLETED')",
            name="ck_token_state",
        ),
    )


# ── QueueEvent ────────────────────────────────────────────────────────────────
# Doc A §3.6 — audit log of all token state transitions

class QueueEvent(Base):
    __tablename__ = "queue_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    token_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tokens.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    from_state: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    to_state: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("staff_users.id"), nullable=True
    )
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    token: Mapped["Token"] = relationship("Token", back_populates="queue_events")
    actor: Mapped[Optional["StaffUser"]] = relationship(
        "StaffUser", back_populates="queue_events"
    )

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('CREATED','CALL_NEXT','HOLD','RECALL','SKIP','COMPLETE')",
            name="ck_queue_event_type",
        ),
        CheckConstraint(
            "actor_type IN ('PATIENT','STAFF','SYSTEM')",
            name="ck_queue_event_actor_type",
        ),
    )


# ── StaffUser ─────────────────────────────────────────────────────────────────
# Doc A §3.7

class StaffUser(Base):
    __tablename__ = "staff_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    username: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    queue_events: Mapped[list["QueueEvent"]] = relationship(
        "QueueEvent", back_populates="actor"
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('RECEPTION','DEPARTMENT_STAFF','ADMIN')",
            name="ck_staff_role",
        ),
    )


# ── Zone ──────────────────────────────────────────────────────────────────────
# Doc A §3.8
# Capacity alert thresholds: UNDECIDED per Doc A — stored as nullable config, not hardcoded.

class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    current_occupancy: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # UNDECIDED thresholds — must be set during demo configuration and testing.
    moderate_threshold: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    high_threshold: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    critical_threshold: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    alert_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    devices: Mapped[list["Device"]] = relationship("Device", back_populates="zone")
    occupancy_events: Mapped[list["OccupancyEvent"]] = relationship(
        "OccupancyEvent", back_populates="zone"
    )


# ── Device ────────────────────────────────────────────────────────────────────
# Doc A §3.9 — represents one ESP32 device monitoring one zone

class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    device_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    zone_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("zones.id"), nullable=False
    )
    firmware_version: Mapped[str] = mapped_column(String(30), nullable=False)
    credential_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    zone: Mapped["Zone"] = relationship("Zone", back_populates="devices")
    occupancy_events: Mapped[list["OccupancyEvent"]] = relationship(
        "OccupancyEvent", back_populates="device"
    )


# ── OccupancyEvent ────────────────────────────────────────────────────────────
# Doc A §3.10 — raw event log from ESP32 device

class OccupancyEvent(Base):
    __tablename__ = "occupancy_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    device_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("devices.id"), nullable=False
    )
    zone_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("zones.id"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(10), nullable=False)
    event_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    occupancy_after: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity_alert: Mapped[str] = mapped_column(String(20), nullable=False)
    firmware_version: Mapped[str] = mapped_column(String(30), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    device: Mapped["Device"] = relationship("Device", back_populates="occupancy_events")
    zone: Mapped["Zone"] = relationship("Zone", back_populates="occupancy_events")

    __table_args__ = (
        UniqueConstraint("device_id", "sequence", name="uq_occupancy_device_sequence"),
        CheckConstraint(
            "event_type IN ('ENTRY','EXIT')",
            name="ck_occupancy_event_type",
        ),
        CheckConstraint(
            "capacity_alert IN ('NORMAL','MODERATE','HIGH','CRITICAL')",
            name="ck_occupancy_capacity_alert",
        ),
    )
