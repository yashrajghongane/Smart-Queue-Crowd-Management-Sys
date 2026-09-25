# SmartQueue — ESP32 Physical Occupancy Sensor Hardware & Firmware

This directory contains the firmware, configuration, and documentation for the **SmartQueue ESP32 Physical Sensing Node**.

The sensing subsystem enforces strict physical traffic monitoring at a clinic or waiting room doorway, completely independent of patient token lifecycles (Document B & System Architecture §1).

---

## 1. Hardware Bill of Materials (BOM)

| Component | Quantity | Purpose | Notes |
|---|---|---|---|
| ESP32 Development Board (ESP32-WROOM-32) | 1 | Microcontroller & Wi-Fi Client | Powered via standard 5 V Micro-USB / Type-C |
| LM393 IR Obstacle Sensor Modules | 2 | Optical beam break detection | Active-LOW output with onboard potentiometer |
| Male-to-Female Jumper Wires | 6 | Sensor to ESP32 connection | ~20 cm length recommended |
| 5 V USB Power Bank or Wall Adapter | 1 | Power source for demo/clinic | 5 V / 1 A minimum |

> [!IMPORTANT]
> **Demo Power:** The ESP32 is powered directly from USB. Do NOT connect a 5 V power source directly to the ESP32 3.3 V pin.

---

## 2. Wiring & Pinout (Document B §1.1)

```
        5 V USB Power
             │
             ▼
      ESP32 Board
   ┌────────────────┐
   │            3V3 ├────────┬────── Sensor A VCC (Pin 1)
   │                │        └────── Sensor B VCC (Pin 1)
   │            GND ├────────┬────── Sensor A GND (Pin 2)
   │                │        └────── Sensor B GND (Pin 2)
   │        GPIO 26 ├─────────────── Sensor A OUT (Pin 3 - Outer / Entrance)
   │        GPIO 27 ├─────────────── Sensor B OUT (Pin 4 - Inner / Room)
   └────────────────┘
```

| Signal | Module Pin | ESP32 Pin | Logic Level |
|---|---|---|---|
| Sensor A OUT | OUT | GPIO 26 | Active LOW when obstacle is present |
| Sensor B OUT | OUT | GPIO 27 | Active LOW when obstacle is present |
| VCC (Both) | VCC | 3V3 | 3.3 V DC Power |
| GND (Both) | GND | GND | Ground Reference |

---

## 3. Physical Placement & Alignment (Document B §1.4)

1. **Mounting Location:** Mount both sensor modules along the **same side** of the entrance frame or corridor.
2. **Spacing:** Sensor A and Sensor B must be mounted **10 cm apart (center-to-center)** along the line of travel:
   - **Sensor A (GPIO 26):** Positioned towards the outside / entrance.
   - **Sensor B (GPIO 27):** Positioned towards the inside / waiting room.
3. **Distance from Corridor:** Sensor emitter/receiver heads should be positioned **10–15 cm** from the walking path.
4. **Mounting:** Sensors must be firmly affixed with brackets or double-sided mounting tape; hand-holding will cause false vibration triggers.

---

## 4. Direction Detection Algorithm

The firmware runs a deterministic finite state machine (FSM):

```
       ┌───────────────────────────┐
       │         STATE_IDLE        │
       └─────┬───────────────┬─────┘
             │               │
      A triggers first   B triggers first
             │               │
             ▼               ▼
   ┌──────────────────┐    ┌──────────────────┐
   │ STATE_A_TRIGGERED│    │ STATE_B_TRIGGERED│
   └─────────┬────────┘    └────────┬─────────┘
             │                      │
       B triggers             A triggers
     within 1500 ms         within 1500 ms
             │                      │
             ▼                      ▼
       [ENTRY EVENT]          [EXIT EVENT]
             │                      │
             └──────────┬───────────┘
                        ▼
             ┌─────────────────────┐
             │   STATE_WAIT_CLEAR  │
             └──────────┬──────────┘
                        │ Both sensors clear
                        ▼
                   STATE_IDLE
```

### Key Operating Rules:
- **Debounce:** Sensor readings must remain stable for **100 ms** before the state transition is accepted.
- **Sequence Timeout:** If the second sensor is not broken within **1500 ms**, the sequence aborts and returns to idle after sensors clear. No false count is sent.
- **Reversal:** If someone triggers Sensor A and turns back without breaking Sensor B, the timeout resets to idle without emitting an event.
- **Simultaneous Trigger:** If both sensors trigger at the exact same instant, the signal is considered ambiguous and ignored.
- **Re-Arm Condition:** Both sensors must be clear before a new movement can be detected.

---

## 5. Security & Authentication Model (Section 6)

Every HTTP request to the backend includes authenticated device headers:
- `X-Device-ID`: Device UUID or code (`DEV-001`).
- `X-Device-Key`: Pre-shared secret key (`esp32-secret-key-001`).

The server:
1. Validates the hash of `X-Device-Key` against the database bcrypt credential.
2. Verifies the device is active and belongs to the specified zone.
3. Enforces idempotency via `(device_id, sequence)` uniqueness. If the ESP32 retries due to a network glitch, the server recognizes the duplicate sequence and does NOT increment occupancy twice.

---

## 6. Setup & Flashing Instructions

### Prerequisites
- [Arduino IDE](https://www.arduino.cc/en/software) (version 2.x recommended) or [PlatformIO](https://platformio.org/).
- ESP32 Board Package installed (`esp32` by Espressif Systems).

### Step-by-Step
1. Open `hardware/esp32/smartqueue_firmware/smartqueue_firmware.ino` in Arduino IDE.
2. In the same directory, create `config.h` (or copy from `../config.example.h`):
   ```c
   const char* const WIFI_SSID     = "Your_WiFi_Name";
   const char* const WIFI_PASSWORD = "Your_WiFi_Password";
   const char* const SERVER_BASE_URL = "http://192.168.1.50:8000"; // Backend IP
   ```
3. In **Tools -> Board**, select **ESP32 Dev Module**.
4. In **Tools -> Port**, select the USB serial port of your ESP32.
5. Click **Upload**.
6. Open **Tools -> Serial Monitor** and set baud rate to **115200**.

---

## 7. Calibration Guide

Each LM393 sensor module has a small blue potentiometer:
1. Power the ESP32 and observe the onboard LED on the LM393 module.
2. With no obstacle in front of the sensor, slowly turn the potentiometer until the detection LED turns OFF.
3. Pass your hand ~15 cm in front of the sensor; the detection LED should turn ON cleanly.
4. Verify both sensors respond independently on the Serial Monitor at 115200 baud.
