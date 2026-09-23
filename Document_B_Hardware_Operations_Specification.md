# Document B — Hardware & Operations Specification

## 0. Scope and reference

This document defines the physical prototype, ESP32 behavior, validation checklist, and demo-day operation.

**Behavior source of truth:** `Workflow & Behavior Document` already completed. This document implements that behavior and does not redefine it.

**Frozen hardware:** 1 ESP32 + 2 wired LM393 IR sensor modules at one waiting-area doorway.

**Demo power:** ESP32 powered from its USB connector using a 5 V power bank/USB source. The battery + MT3608 chain is future work and is not part of this demo hardware path.

---

## 1. Wiring

### 1.1 ESP32 and sensor pin assignment

| Signal | Component | ESP32 pin |
|---|---|---|
| Sensor A OUT | LM393 IR module A | GPIO 26 |
| Sensor B OUT | LM393 IR module B | GPIO 27 |
| Sensor A VCC | LM393 IR module A | 3V3 |
| Sensor B VCC | LM393 IR module B | 3V3 |
| Sensor A GND | LM393 IR module A | GND |
| Sensor B GND | LM393 IR module B | GND |

### 1.2 Optional external pull-ups

Use one **10 kΩ resistor from each sensor OUT to 3V3** only if the purchased module output is open-collector/open-drain without a built-in pull-up.

- Sensor A: GPIO26 → 10 kΩ → 3V3
- Sensor B: GPIO27 → 10 kΩ → 3V3

If the module already has a pull-up/output driver, the external resistor may be omitted.

**Hardware value that must be checked on the purchased module:** active output level. Default firmware setting is `LOW = DETECTED`; invert the configured detection level if bench testing shows the module behaves as `HIGH = DETECTED`.

### 1.3 Power wiring

```text
5 V USB Power Bank
        │
        ▼
 ESP32 USB power input
        │
        ├──────── 3V3 ────── Sensor A VCC
        │
        ├──────── 3V3 ────── Sensor B VCC
        │
        └──────── GND ────── Sensor A GND + Sensor B GND
```

Do **not** connect the demo power bank directly to the ESP32 3.3 V pin.

### 1.4 Sensor placement

For the current prototype:

- Sensor A and Sensor B are mounted on the **same side** of the doorway/path.
- Center-to-center spacing: **10 cm** along the direction of travel.
- Keep both sensors aimed at the same detection corridor.
- Start with the sensor heads approximately **10–15 cm from the path edge** and adjust only during calibration so the person's body reliably enters both sensing zones.
- The two sensors must be physically fixed; do not hand-hold them during the demo.

**Undecided value:** exact final mounting height. It depends on the physical doorway and the purchased sensor's actual detection geometry, so it must be set during bench/doorway calibration rather than invented in software.

---

## 2. Firmware behavior

### 2.1 GPIO sampling

| Parameter | Value |
|---|---:|
| Sensor A GPIO | 26 |
| Sensor B GPIO | 27 |
| Default detected level | LOW |
| Debounce/stability time | **100 ms** |
| Sequence timeout | **1500 ms** |
| Re-arm condition | Both sensors clear after the current sequence |
| Event sequence counter | Increment by 1 for every emitted ENTRY/EXIT event |
| Event types | `ENTRY`, `EXIT` only |
| Timestamp | UTC ISO-8601 after NTP synchronization |

### 2.2 Event interpretation

```text
IDLE
  │
  ├── A detected first ──► WAIT_B
  │                         │
  │                         ├── B detected within 1500 ms ──► ENTRY
  │                         └── timeout ──► IDLE after both clear
  │
  └── B detected first ──► WAIT_A
                            │
                            ├── A detected within 1500 ms ──► EXIT
                            └── timeout ──► IDLE after both clear
```

### 2.3 Debounce rule

A sensor transition is accepted only when its detected/not-detected state remains stable for **100 ms**.

Short pulses shorter than 100 ms are ignored.

### 2.4 Incomplete A/B sequence

Example:

```text
A detected
   ↓
B never detected for 1500 ms
   ↓
No ENTRY/EXIT emitted
```

The device returns to the idle state after both sensors are clear.

### 2.5 Person reverses direction

If a person triggers only the first sensor and turns around before completing the second-sensor sequence, no event is emitted.

If a person fully crosses and then genuinely returns:

```text
A → B = ENTRY
B → A = EXIT
```

This is treated as two real movement events.

### 2.6 Two people crossing together

The two-sensor prototype cannot reliably distinguish two overlapping people from one person when their sensor interruptions overlap.

Contract:
- Emit one event for each confidently completed A→B or B→A sequence.
- Do not fabricate a second event when the hardware cannot distinguish it.
- Record this as a known prototype limitation during testing.

### 2.7 Device event JSON

The ESP32 must POST exactly this JSON shape to the Document A device endpoint:

```json
{
  "device_id": "DEV-001",
  "zone_id": "ZONE-001",
  "sequence": 123,
  "event_type": "ENTRY",
  "event_at": "2026-09-23T16:10:32.420Z",
  "firmware_version": "0.1.0"
}
```

Rules:
- `device_id`: fixed identifier assigned to the prototype.
- `zone_id`: fixed identifier for the monitored waiting area.
- `sequence`: monotonically increasing integer; never reuse a sequence number after an event has been emitted.
- `event_type`: exactly `ENTRY` or `EXIT`.
- `event_at`: UTC ISO-8601 timestamp.
- `firmware_version`: semantic version string, starting at `0.1.0` for the demo.

### 2.8 Server response expected by firmware

```json
{
  "device_id": "DEV-001",
  "zone_id": "ZONE-001",
  "sequence": 123,
  "accepted": true,
  "event_type": "ENTRY",
  "occupancy": 8,
  "capacity_alert": "HIGH",
  "processed_at": "2026-09-23T16:10:32.470Z"
}
```

The firmware does not change token states from this response. It only reports physical events.

---

## 3. Test checklist

| # | Test | Pass condition |
|---:|---|---|
| 1 | Power-on | ESP32 starts and connects to configured network |
| 2 | Sensor A detection | A is detected consistently when an object/person crosses its sensing area |
| 3 | Sensor B detection | B is detected consistently |
| 4 | A → B movement | Exactly one `ENTRY` event is emitted |
| 5 | B → A movement | Exactly one `EXIT` event is emitted |
| 6 | One sensor only | No ENTRY/EXIT and no occupancy change |
| 7 | Reversal before second sensor | No false ENTRY/EXIT |
| 8 | Two-person close crossing | Behavior recorded; prototype limitation documented if counted as one |
| 9 | Duplicate registration | Second active registration returns existing active token instead of creating another |
| 10 | CALL NEXT once | One WAITING token becomes SERVING |
| 11 | CALL NEXT twice concurrently | Same token is never assigned twice; second request gets the next eligible token or `NO_WAITING_TOKENS` |
| 12 | HOLD / RECALL / SKIP / COMPLETE | Only valid state transitions succeed; invalid transitions return `409` |
| 13 | Dashboard sync | Queue state and occupancy update independently |
| 14 | Device event duplicate | Reusing the same `(device_id, sequence)` does not increment occupancy twice |
| 15 | Capacity alert | Alert changes only when occupancy crosses configured threshold values |

**Undecided value:** numeric capacity thresholds for `NORMAL/MODERATE/HIGH/CRITICAL`. These must be set before the final demo configuration and copied identically into the Zone configuration used by the backend.

---

## 4. Demo-day script

### Before judges arrive

1. Power the ESP32 from the 5 V power bank.
2. Start the FastAPI backend and database.
3. Open the staff dashboard, patient view, and public display.
4. Confirm the physical zone starts from a known occupancy value.
5. Confirm both IR sensors are detecting correctly.
6. Confirm the device shows a successful connection to the backend.

### Live demonstration

#### Step 1 — Patient with phone

1. Show the QR/web registration screen.
2. Register Patient A.
3. Show Visit + Token creation.
4. Show Token A in `WAITING`.

#### Step 2 — Patient without phone

5. Open the same registration function as staff.
6. Register Patient B using staff-assisted registration.
7. Show Patient B receives a normal queue token.
8. Point out that both patients enter the same queue.

#### Step 3 — Queue operation

9. On the staff dashboard, press **CALL NEXT**.
10. Show the first token changing `WAITING → SERVING`.
11. Show the public display changing to the called token.
12. Demonstrate **HOLD** on a token.
13. Demonstrate **RECALL** returning it to active queue handling.
14. Demonstrate **SKIP** on another waiting token.
15. Demonstrate **COMPLETE** on the serving token.

#### Step 4 — Physical sensing

16. Have one person cross the monitored doorway in the A → B direction.
17. Show `ENTRY` and occupancy increasing by 1.
18. Have the person return B → A.
19. Show `EXIT` and occupancy decreasing by 1.
20. Trigger only one sensor and show that occupancy does not change.

#### Step 5 — Combined dashboard view

21. Create additional waiting tokens so the queue count changes.
22. Move people through the monitored doorway so occupancy changes separately.
23. Point to the two independent values on the dashboard.
24. Trigger enough physical occupancy to show a capacity-level alert change using the configured thresholds.

#### Final statement to judges

25. Show that **staff actions control the patient queue**, while **the sensor only reports physical movement and occupancy**.
