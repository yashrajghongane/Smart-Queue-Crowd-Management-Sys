"""
app/services/occupancy_service.py

ENTRY/EXIT validation, occupancy update, capacity-alert calculation, idempotency.

CURRENT STATUS: Deferred — hardware integration is a later milestone.
This module is reserved for the ESP32/sensor integration milestone.

Do not implement occupancy logic here until the hardware milestone begins.
"""
from sqlalchemy.orm import Session


class OccupancyService:
    """
    Owns all occupancy transitions.
    Deferred to the hardware integration milestone.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def process_device_event(self, event_data: dict) -> dict:
        """
        Validate and record an ENTRY/EXIT event from an ESP32 device.
        Enforces idempotency via (device_id, sequence) uniqueness. Doc A §2.11.
        DEFERRED — not implemented until the hardware milestone.
        """
        raise NotImplementedError(
            "Occupancy service is implemented in the hardware integration milestone."
        )
