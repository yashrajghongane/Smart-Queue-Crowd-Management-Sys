from fastapi import APIRouter, HTTPException
from app.schemas.schemas import DeviceEventRequest, DeviceEventResponse

router = APIRouter()

@router.post(
    "/events",
    response_model=DeviceEventResponse,
    summary="Device event ingestion (DEFERRED — hardware milestone)",
    description=(
        "Accepts ENTRY/EXIT events from the ESP32 sensor device. "
        "Deferred to the hardware integration milestone. Doc A §2.11."
    ),
)
def ingest_device_event(body: DeviceEventRequest):
    raise HTTPException(
        status_code=501,
        detail=(
            "Device event ingestion is deferred to the hardware integration milestone. "
            "The ESP32 firmware and occupancy logic are not yet implemented."
        ),
    )
