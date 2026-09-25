"""
app/services/occupancy_service.py

Authoritative business logic for:
- ENTRY / EXIT physical occupancy transitions
- Capacity calculation & threshold alerts (NORMAL, MODERATE, HIGH, CRITICAL)
- Idempotent device event ingestion via (device_id, sequence) uniqueness
- Device last-seen and sequence tracking
- Zone crowd and occupancy summaries for staff dashboard

Sole owner of occupancy state transitions (Document A §5, Workflow §16).
"""
from __future__ import annotations
from datetime import datetime, date, time
from typing import Optional, Any
from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session

from app.models.models import Zone, Device, OccupancyEvent, _new_uuid, _utcnow


class OccupancyServiceError(ValueError):
    pass


class ZoneNotFoundError(OccupancyServiceError):
    pass


class DeviceNotFoundError(OccupancyServiceError):
    pass


class DeviceInactiveError(OccupancyServiceError):
    pass


class InvalidDeviceEventError(OccupancyServiceError):
    pass


class OccupancyService:
    """
    Owns all physical occupancy transitions and crowd calculations.
    Ensures strict separation between digital queue tokens and physical occupancy.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def _calculate_capacity_alert(self, occupancy: int, zone: Zone) -> str:
        """
        Evaluate occupancy against zone thresholds:
        - NORMAL: below moderate threshold
        - MODERATE: moderate threshold to high threshold
        - HIGH: high threshold to critical threshold
        - CRITICAL: at or above critical threshold
        """
        crit = zone.critical_threshold if zone.critical_threshold is not None else zone.capacity
        high = zone.high_threshold if zone.high_threshold is not None else int(zone.capacity * 0.8)
        mod = zone.moderate_threshold if zone.moderate_threshold is not None else int(zone.capacity * 0.6)

        if occupancy >= crit:
            return "CRITICAL"
        elif occupancy >= high:
            return "HIGH"
        elif occupancy >= mod:
            return "MODERATE"
        return "NORMAL"

    def process_device_event(
        self,
        device_id: str,
        zone_id: str,
        sequence: int,
        event_type: str,
        event_at: datetime,
        firmware_version: str,
    ) -> dict[str, Any]:
        """
        Validate and record an ENTRY/EXIT event from an ESP32 device.
        Enforces idempotency via (device_id, sequence) uniqueness.
        Document A §2.11.
        """
        if sequence <= 0:
            raise InvalidDeviceEventError("Sequence number must be a positive integer.")

        if event_type not in ("ENTRY", "EXIT"):
            raise InvalidDeviceEventError(f"Invalid event_type '{event_type}'. Must be ENTRY or EXIT.")

        # 1. Lookup device
        device = (
            self.db.query(Device)
            .filter((Device.id == device_id) | (Device.device_code == device_id))
            .first()
        )
        if device is None:
            raise DeviceNotFoundError(f"Device '{device_id}' not found.")

        if not device.active:
            raise DeviceInactiveError(f"Device '{device.device_code}' is deactivated.")

        # 2. Lookup zone with row lock
        zone = (
            self.db.execute(
                select(Zone).where(Zone.id == zone_id).with_for_update()
            )
            .scalar_one_or_none()
        )
        if zone is None:
            raise ZoneNotFoundError(f"Zone '{zone_id}' not found.")

        # Verify device belongs to this zone
        if device.zone_id != zone.id:
            raise InvalidDeviceEventError(
                f"Device '{device.device_code}' is mapped to zone '{device.zone_id}', not '{zone_id}'."
            )

        # 3. Idempotency Check: (device_id, sequence)
        existing_event = (
            self.db.query(OccupancyEvent)
            .filter(
                OccupancyEvent.device_id == device.id,
                OccupancyEvent.sequence == sequence,
            )
            .first()
        )
        if existing_event is not None:
            # Duplicate sequence: return existing state with accepted=False
            return {
                "device_id": device.id,
                "zone_id": zone.id,
                "sequence": sequence,
                "accepted": False,
                "event_type": existing_event.event_type,
                "occupancy": existing_event.occupancy_after,
                "capacity_alert": existing_event.capacity_alert,
                "processed_at": existing_event.received_at,
            }

        # 4. Calculate new occupancy
        current_occ = zone.current_occupancy or 0
        if event_type == "ENTRY":
            new_occupancy = current_occ + 1
        elif event_type == "EXIT":
            new_occupancy = max(0, current_occ - 1)
        else:
            new_occupancy = current_occ

        # 5. Calculate capacity alert
        alert = self._calculate_capacity_alert(new_occupancy, zone)
        now = _utcnow()

        # 6. Record OccupancyEvent
        event_record = OccupancyEvent(
            id=_new_uuid(),
            device_id=device.id,
            zone_id=zone.id,
            sequence=sequence,
            event_type=event_type,
            event_at=event_at,
            occupancy_after=new_occupancy,
            capacity_alert=alert,
            firmware_version=firmware_version,
            received_at=now,
        )
        self.db.add(event_record)

        # 7. Update Zone & Device
        zone.current_occupancy = new_occupancy
        device.last_seen_at = now
        device.last_sequence = sequence
        device.firmware_version = firmware_version

        self.db.commit()

        return {
            "device_id": device.id,
            "zone_id": zone.id,
            "sequence": sequence,
            "accepted": True,
            "event_type": event_type,
            "occupancy": new_occupancy,
            "capacity_alert": alert,
            "processed_at": now,
        }

    def get_zone_occupancy(self, zone_id: str) -> Optional[dict[str, Any]]:
        """
        Read-only summary of zone occupancy (Document A §2.10).
        """
        zone = (
            self.db.query(Zone)
            .filter((Zone.id == zone_id) | (Zone.name == zone_id))
            .first()
        )
        if zone is None:
            return None

        occupancy = zone.current_occupancy or 0
        alert = self._calculate_capacity_alert(occupancy, zone)

        # Find latest event timestamp
        latest_event = (
            self.db.query(OccupancyEvent)
            .filter(OccupancyEvent.zone_id == zone.id)
            .order_by(OccupancyEvent.received_at.desc())
            .first()
        )
        updated_at = latest_event.received_at if latest_event else zone.created_at

        return {
            "zone_id": zone.id,
            "occupancy": occupancy,
            "capacity": zone.capacity,
            "capacity_alert": alert,
            "updated_at": updated_at,
        }

    def get_crowd_detail(self, zone_id: str) -> Optional[dict[str, Any]]:
        """
        Detailed physical crowd status for Staff Dashboard (Section 8 & 9).
        Includes entries today, exits today, net change, and device diagnostic status.
        """
        zone = (
            self.db.query(Zone)
            .filter((Zone.id == zone_id) | (Zone.name == zone_id))
            .first()
        )
        if zone is None:
            return None

        occupancy = zone.current_occupancy or 0
        capacity = zone.capacity or 1
        utilization = round((occupancy / capacity) * 100.0, 1)
        alert = self._calculate_capacity_alert(occupancy, zone)

        # Calculate entries and exits today (UTC)
        today_start = datetime.combine(date.today(), time.min)
        entries_today = (
            self.db.query(func.count(OccupancyEvent.id))
            .filter(
                OccupancyEvent.zone_id == zone.id,
                OccupancyEvent.event_type == "ENTRY",
                OccupancyEvent.received_at >= today_start,
            )
            .scalar()
            or 0
        )
        exits_today = (
            self.db.query(func.count(OccupancyEvent.id))
            .filter(
                OccupancyEvent.zone_id == zone.id,
                OccupancyEvent.event_type == "EXIT",
                OccupancyEvent.received_at >= today_start,
            )
            .scalar()
            or 0
        )
        net_change = entries_today - exits_today

        # Latest event
        latest_event = (
            self.db.query(OccupancyEvent)
            .filter(OccupancyEvent.zone_id == zone.id)
            .order_by(OccupancyEvent.received_at.desc())
            .first()
        )

        # Linked device status
        device = (
            self.db.query(Device)
            .filter(Device.zone_id == zone.id)
            .first()
        )

        now = _utcnow()
        if device is None:
            dev_status = "NO_DEVICE"
        elif not device.active:
            dev_status = "OFFLINE"
        elif device.last_seen_at is None:
            dev_status = "OFFLINE"
        elif (now - device.last_seen_at).total_seconds() > 300:  # 5 minutes stale threshold
            dev_status = "STALE"
        else:
            dev_status = "ONLINE"

        return {
            "zone_id": zone.id,
            "zone_name": zone.name,
            "occupancy": occupancy,
            "capacity": zone.capacity,
            "utilization_percent": utilization,
            "capacity_alert": alert,
            "entries_today": entries_today,
            "exits_today": exits_today,
            "net_change_today": net_change,
            "last_event_type": latest_event.event_type if latest_event else None,
            "last_event_time": latest_event.event_at if latest_event else None,
            "last_sequence": latest_event.sequence if latest_event else (device.last_sequence if device else None),
            "device_id": device.id if device else None,
            "device_code": device.device_code if device else None,
            "device_status": dev_status,
            "firmware_version": device.firmware_version if device else None,
            "last_seen_at": device.last_seen_at if device else None,
            "updated_at": latest_event.received_at if latest_event else now,
        }
