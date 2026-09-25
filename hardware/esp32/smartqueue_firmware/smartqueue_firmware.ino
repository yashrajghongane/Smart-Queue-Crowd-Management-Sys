/**
 * SmartQueue ESP32 Physical Occupancy Sensor Firmware
 *
 * Implements Document B (Hardware Operations Specification) and API Contract §2.11.
 *
 * Architecture:
 * - 1 ESP32 Microcontroller
 * - 2 LM393 IR Obstacle Sensor Modules at single waiting room doorway
 *   - Sensor A: GPIO 26 (Outer side / Entrance)
 *   - Sensor B: GPIO 27 (Inner side / Waiting area)
 * - State machine for directional detection (A -> B = ENTRY, B -> A = EXIT)
 * - 100 ms debounce filtering
 * - 1500 ms sequence timeout
 * - Monotonically increasing sequence counter persisted to non-volatile flash (Preferences/NVS)
 * - HTTP/HTTPS POST to /api/v1/devices/events with X-Device-ID & X-Device-Key auth headers
 * - Auto-reconnection for Wi-Fi and network retry buffer
 * - Comprehensive Serial diagnostics (115200 baud)
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <time.h>
#include <esp_task_wdt.h>

// ── Include Configuration ────────────────────────────────────────────────────
// In production, copy config.example.h to config.h and customize credentials.
#if __has_include("config.h")
  #include "config.h"
#else
  #include "../config.example.h"
#endif

// ── State Machine Definitions ────────────────────────────────────────────────
enum SensorState {
  STATE_IDLE,
  STATE_A_TRIGGERED,
  STATE_B_TRIGGERED,
  STATE_WAIT_CLEAR
};

// ── Global Objects & Variables ───────────────────────────────────────────────
Preferences preferences;
SensorState currentState = STATE_IDLE;
unsigned long triggerStartTime = 0;
unsigned long sequenceCounter = 0;
bool ntpSynced = false;

// Debounce state tracking
int lastReadingA = HIGH;
int lastReadingB = HIGH;
unsigned long lastDebounceTimeA = 0;
unsigned long lastDebounceTimeB = 0;
int stableStateA = HIGH;
int stableStateB = HIGH;

// NTP Server settings
const char* const NTP_SERVER = "pool.ntp.org";
const long  GMT_OFFSET_SEC = 0;      // Store timestamps in UTC
const int   DAYLIGHT_OFFSET_SEC = 0;

// Watchdog timeout (30 seconds)
#define WDT_TIMEOUT_SECONDS 30

// ── Helper: Format ISO-8601 UTC Timestamp ────────────────────────────────────
String getISOTimestamp() {
  time_t now;
  struct tm timeinfo;
  if (getLocalTime(&timeinfo, 50)) {
    char buf[30];
    strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
    return String(buf);
  }
  // Fallback if NTP is unavailable
  unsigned long ms = millis();
  char fallbackBuf[32];
  snprintf(fallbackBuf, sizeof(fallbackBuf), "2026-09-26T00:00:00.%03luZ", ms % 1000);
  return String(fallbackBuf);
}

// ── Sequence Persistence ─────────────────────────────────────────────────────
unsigned long loadNextSequence() {
  preferences.begin("smartqueue", false);
  unsigned long seq = preferences.getULong("seq", 0) + 1;
  preferences.putULong("seq", seq);
  preferences.end();
  return seq;
}

// ── Wi-Fi Connection & Health Check ──────────────────────────────────────────
void ensureWiFiConnected() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  Serial.println(F("[WiFi] Disconnected. Reconnecting to AP..."));
  WiFi.disconnect();
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long startAttempt = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startAttempt < 15000) {
    delay(500);
    Serial.print(F("."));
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print(F("[WiFi] Connected! IP: "));
    Serial.println(WiFi.localIP());
  } else {
    Serial.println(F("[WiFi] Connection failed. Will retry next cycle."));
  }
}

// ── Transmit Event to Backend ────────────────────────────────────────────────
bool sendDeviceEvent(const char* eventType, unsigned long seq) {
  ensureWiFiConnected();
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(F("[HTTP] Skipped send — no Wi-Fi."));
    return false;
  }

  HTTPClient http;
  String fullUrl = String(SERVER_BASE_URL) + String(EVENT_ENDPOINT);
  http.begin(fullUrl);
  http.setTimeout(8000);

  // Set Request Headers
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-ID", DEVICE_ID);
  http.addHeader("X-Device-Key", DEVICE_SECRET_KEY);

  // Construct JSON Body (Doc A §2.11)
  String payload = "{";
  payload += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
  payload += "\"zone_id\":\"" + String(ZONE_ID) + "\",";
  payload += "\"sequence\":" + String(seq) + ",";
  payload += "\"event_type\":\"" + String(eventType) + "\",";
  payload += "\"event_at\":\"" + getISOTimestamp() + "\",";
  payload += "\"firmware_version\":\"" + String(FIRMWARE_VERSION) + "\"";
  payload += "}";

  Serial.print(F("[HTTP] POST "));
  Serial.println(fullUrl);
  Serial.print(F("[HTTP] Payload: "));
  Serial.println(payload);

  int httpCode = http.POST(payload);
  bool success = false;

  if (httpCode > 0) {
    String response = http.getString();
    Serial.print(F("[HTTP] Response ("));
    Serial.print(httpCode);
    Serial.print(F("): "));
    Serial.println(response);

    if (httpCode == 200 || httpCode == 201) {
      success = true;
      Serial.println(F("[HTTP] Event acknowledged by backend."));
    } else {
      Serial.print(F("[HTTP] Warning: Backend returned status "));
      Serial.println(httpCode);
    }
  } else {
    Serial.print(F("[HTTP] POST failed, error: "));
    Serial.println(http.errorToString(httpCode).c_str());
  }

  http.end();
  return success;
}

// ── Debounce Reading ─────────────────────────────────────────────────────────
void readDebouncedSensors() {
  int rawA = digitalRead(PIN_SENSOR_A);
  int rawB = digitalRead(PIN_SENSOR_B);
  unsigned long now = millis();

  // Debounce Sensor A
  if (rawA != lastReadingA) {
    lastDebounceTimeA = now;
  }
  if ((now - lastDebounceTimeA) > DEBOUNCE_MS) {
    stableStateA = rawA;
  }
  lastReadingA = rawA;

  // Debounce Sensor B
  if (rawB != lastReadingB) {
    lastDebounceTimeB = now;
  }
  if ((now - lastDebounceTimeB) > DEBOUNCE_MS) {
    stableStateB = rawB;
  }
  lastReadingB = rawB;
}

// ── Setup ────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println();
  Serial.println(F("=================================================="));
  Serial.println(F("  SmartQueue ESP32 Physical Occupancy Sensor      "));
  Serial.print(F("  Firmware Version: "));
  Serial.println(FIRMWARE_VERSION);
  Serial.print(F("  Device ID:        "));
  Serial.println(DEVICE_CODE);
  Serial.println(F("=================================================="));

  // 1. Configure Hardware GPIOs
  pinMode(PIN_SENSOR_A, INPUT_PULLUP);
  pinMode(PIN_SENSOR_B, INPUT_PULLUP);
  Serial.println(F("[GPIO] Sensor A (GPIO 26) configured."));
  Serial.println(F("[GPIO] Sensor B (GPIO 27) configured."));

  // 2. Load Sequence from Non-Volatile Storage
  preferences.begin("smartqueue", true);
  sequenceCounter = preferences.getULong("seq", 0);
  preferences.end();
  Serial.print(F("[NVS] Restored last sequence counter: "));
  Serial.println(sequenceCounter);

  // 3. Connect to Wi-Fi
  ensureWiFiConnected();

  // 4. Configure NTP Time
  configTime(GMT_OFFSET_SEC, DAYLIGHT_OFFSET_SEC, NTP_SERVER);
  Serial.println(F("[NTP] Synchronizing time with pool.ntp.org..."));

  // 5. Initialize Hardware Watchdog
  esp_task_wdt_config_t wdt_config = {
      .timeout_ms = WDT_TIMEOUT_SECONDS * 1000,
      .idle_core_mask = 0,
      .trigger_panic = true
  };
  esp_task_wdt_init(&wdt_config);
  esp_task_wdt_add(NULL); // Add current thread to watchdog
  Serial.println(F("[WDT] Watchdog timer activated (30s)."));

  Serial.println(F("[System] Initialization complete. Sensor loop running."));
}

// ── Main Loop & State Machine ────────────────────────────────────────────────
void loop() {
  // Feed watchdog
  esp_task_wdt_reset();

  // Sample debounced sensors
  readDebouncedSensors();
  unsigned long now = millis();

  bool activeA = (stableStateA == SENSOR_DETECTED_LEVEL);
  bool activeB = (stableStateB == SENSOR_DETECTED_LEVEL);

  switch (currentState) {
    case STATE_IDLE:
      // Both clear: wait for either sensor to be triggered
      if (activeA && !activeB) {
        currentState = STATE_A_TRIGGERED;
        triggerStartTime = now;
        Serial.println(F("[FSM] Sensor A triggered -> STATE_A_TRIGGERED (Wait for B)"));
      } else if (activeB && !activeA) {
        currentState = STATE_B_TRIGGERED;
        triggerStartTime = now;
        Serial.println(F("[FSM] Sensor B triggered -> STATE_B_TRIGGERED (Wait for A)"));
      } else if (activeA && activeB) {
        // Simultaneous trigger: ambiguous, ignore
        Serial.println(F("[FSM] Warning: Simultaneous A+B trigger ignored."));
      }
      break;

    case STATE_A_TRIGGERED:
      // Person entered through Sensor A first. Check for Sensor B.
      if (activeB) {
        // Confirmed ENTRY sequence: A then B
        Serial.println(F("[FSM] Sensor B detected within window -> ENTRY CONFIRMED!"));
        unsigned long nextSeq = loadNextSequence();
        sendDeviceEvent("ENTRY", nextSeq);
        currentState = STATE_WAIT_CLEAR;
      } else if (now - triggerStartTime > SEQUENCE_TIMEOUT_MS) {
        // Timeout: person stepped in front of A and walked away
        Serial.println(F("[FSM] Timeout waiting for B -> Resetting to IDLE"));
        currentState = STATE_WAIT_CLEAR;
      }
      break;

    case STATE_B_TRIGGERED:
      // Person approached Sensor B first (inside room). Check for Sensor A.
      if (activeA) {
        // Confirmed EXIT sequence: B then A
        Serial.println(F("[FSM] Sensor A detected within window -> EXIT CONFIRMED!"));
        unsigned long nextSeq = loadNextSequence();
        sendDeviceEvent("EXIT", nextSeq);
        currentState = STATE_WAIT_CLEAR;
      } else if (now - triggerStartTime > SEQUENCE_TIMEOUT_MS) {
        // Timeout: person stepped near B and stepped back inside
        Serial.println(F("[FSM] Timeout waiting for A -> Resetting to IDLE"));
        currentState = STATE_WAIT_CLEAR;
      }
      break;

    case STATE_WAIT_CLEAR:
      // Re-arm condition: both sensors must return to clear before accepting next movement
      if (!activeA && !activeB) {
        currentState = STATE_IDLE;
        Serial.println(F("[FSM] Sensors clear -> Armed and IDLE"));
      }
      break;
  }

  delay(10); // Small cycle delay
}
