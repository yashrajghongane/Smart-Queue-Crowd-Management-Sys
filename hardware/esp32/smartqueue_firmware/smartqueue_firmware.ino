/**
 * SmartQueue ESP32 Physical Occupancy Sensor Firmware
 *
 * Implements:
 * - Document B (Hardware Operations Specification)
 * - API Contract §2.11 (Device Event Ingestion)
 * - Secure TLS validation (ISRG Root X1) without setInsecure()
 * - Reliable offline queue with non-volatile flash (NVS) persistence
 * - Direction detection finite-state machine (A -> B = ENTRY, B -> A = EXIT)
 * - 100 ms debounce filtering and 1500 ms sequence timeout
 * - Monotonic sequence persistence across reboots
 */

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <time.h>
#include <esp_task_wdt.h>

// ── Include Configuration ────────────────────────────────────────────────────
// In production, create config.h locally (ignored by git) or use config.example.h
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

// ── Offline Event Structure ──────────────────────────────────────────────────
#define MAX_OFFLINE_EVENTS 32

struct PendingEvent {
  unsigned long sequence;
  char eventType[8];     // "ENTRY" or "EXIT"
  char timestamp[32];    // ISO-8601 UTC
  bool active;
};

// ── Global Objects & Variables ───────────────────────────────────────────────
Preferences preferences;
SensorState currentState = STATE_IDLE;
unsigned long triggerStartTime = 0;
unsigned long sequenceCounter = 0;
unsigned long lastRetryAttempt = 0;

PendingEvent eventQueue[MAX_OFFLINE_EVENTS];

// Debounce state tracking
int lastReadingA = HIGH;
int lastReadingB = HIGH;
unsigned long lastDebounceTimeA = 0;
unsigned long lastDebounceTimeB = 0;
int stableStateA = HIGH;
int stableStateB = HIGH;

// NTP Server settings
const char* const NTP_SERVER = "pool.ntp.org";
const long  GMT_OFFSET_SEC = 0;
const int   DAYLIGHT_OFFSET_SEC = 0;

#define WDT_TIMEOUT_SECONDS 30

// ── Helper: ISO-8601 Timestamp ───────────────────────────────────────────────
String getISOTimestamp() {
  time_t now;
  struct tm timeinfo;
  if (getLocalTime(&timeinfo, 50)) {
    char buf[30];
    strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
    return String(buf);
  }
  unsigned long ms = millis();
  char fallbackBuf[32];
  snprintf(fallbackBuf, sizeof(fallbackBuf), "2026-09-26T00:00:00.%03luZ", ms % 1000);
  return String(fallbackBuf);
}

// ── NVS Sequence Management ──────────────────────────────────────────────────
unsigned long loadNextSequence() {
  preferences.begin("smartqueue", false);
  unsigned long seq = preferences.getULong("seq", 0) + 1;
  preferences.putULong("seq", seq);
  preferences.end();
  return seq;
}

// ── Offline Event Queue Management ───────────────────────────────────────────
void enqueueEvent(const char* eventType, unsigned long seq, const String& ts) {
  for (int i = 0; i < MAX_OFFLINE_EVENTS; i++) {
    if (!eventQueue[i].active) {
      eventQueue[i].sequence = seq;
      strncpy(eventQueue[i].eventType, eventType, sizeof(eventQueue[i].eventType) - 1);
      eventQueue[i].eventType[sizeof(eventQueue[i].eventType) - 1] = '\0';
      strncpy(eventQueue[i].timestamp, ts.c_str(), sizeof(eventQueue[i].timestamp) - 1);
      eventQueue[i].timestamp[sizeof(eventQueue[i].timestamp) - 1] = '\0';
      eventQueue[i].active = true;

      // Persist to NVS as pending
      preferences.begin("sq_queue", false);
      char key[16];
      snprintf(key, sizeof(key), "ev_%d", i);
      preferences.putBytes(key, &eventQueue[i], sizeof(PendingEvent));
      preferences.end();

      Serial.print(F("[Queue] Enqueued "));
      Serial.print(eventType);
      Serial.print(F(" #"));
      Serial.print(seq);
      Serial.print(F(" at slot "));
      Serial.println(i);
      return;
    }
  }
  Serial.println(F("[Queue] Warning: Event queue full! Event dropped."));
}

void clearQueueSlot(int slot) {
  if (slot >= 0 && slot < MAX_OFFLINE_EVENTS) {
    eventQueue[slot].active = false;
    preferences.begin("sq_queue", false);
    char key[16];
    snprintf(key, sizeof(key), "ev_%d", slot);
    preferences.remove(key);
    preferences.end();
  }
}

void restoreQueueFromNVS() {
  preferences.begin("sq_queue", true);
  for (int i = 0; i < MAX_OFFLINE_EVENTS; i++) {
    char key[16];
    snprintf(key, sizeof(key), "ev_%d", i);
    if (preferences.isKey(key)) {
      preferences.getBytes(key, &eventQueue[i], sizeof(PendingEvent));
      if (eventQueue[i].active) {
        Serial.print(F("[NVS] Restored pending event slot "));
        Serial.print(i);
        Serial.print(F(": "));
        Serial.print(eventQueue[i].eventType);
        Serial.print(F(" #"));
        Serial.println(eventQueue[i].sequence);
      }
    } else {
      eventQueue[i].active = false;
    }
  }
  preferences.end();
}

// ── Wi-Fi Management ─────────────────────────────────────────────────────────
void ensureWiFiConnected() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }
  Serial.println(F("[WiFi] Disconnected. Reconnecting..."));
  WiFi.disconnect();
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 10000) {
    delay(500);
    Serial.print(F("."));
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print(F("[WiFi] Connected! IP: "));
    Serial.println(WiFi.localIP());
  } else {
    Serial.println(F("[WiFi] Reconnection failed. Event held in offline queue."));
  }
}

// ── Transmit Single Event (HTTPS / HTTP with TLS Validation) ──────────────────
bool transmitEvent(const char* eventType, unsigned long seq, const char* ts) {
  ensureWiFiConnected();
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  String fullUrl = String(SERVER_BASE_URL) + String(EVENT_ENDPOINT);
  HTTPClient http;
  bool isHttps = fullUrl.startsWith("https://");

  WiFiClientSecure secureClient;
  if (isHttps) {
    // Real TLS root certificate verification (ISRG Root X1)
    secureClient.setCACert(ROOT_CA_CERTIFICATE);
    http.begin(secureClient, fullUrl);
  } else {
    WiFiClient plainClient;
    http.begin(plainClient, fullUrl);
  }

  http.setTimeout(8000);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-ID", DEVICE_ID);
  http.addHeader("X-Device-Key", DEVICE_SECRET_KEY);

  String payload = "{";
  payload += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
  payload += "\"zone_id\":\"" + String(ZONE_ID) + "\",";
  payload += "\"sequence\":" + String(seq) + ",";
  payload += "\"event_type\":\"" + String(eventType) + "\",";
  payload += "\"event_at\":\"" + String(ts) + "\",";
  payload += "\"firmware_version\":\"" + String(FIRMWARE_VERSION) + "\"";
  payload += "}";

  Serial.print(F("[HTTP] POST "));
  Serial.print(fullUrl);
  Serial.print(F(" (seq: "));
  Serial.print(seq);
  Serial.println(F(")"));

  int httpCode = http.POST(payload);
  bool success = false;

  if (httpCode > 0) {
    String response = http.getString();
    Serial.print(F("[HTTP] Status "));
    Serial.print(httpCode);
    Serial.print(F(" -> "));
    Serial.println(response);

    // 200 or 201 means server accepted or duplicate handled (both acknowledged)
    if (httpCode == 200 || httpCode == 201) {
      success = true;
    }
  } else {
    Serial.print(F("[HTTP] Transmission error: "));
    Serial.println(http.errorToString(httpCode).c_str());
  }

  http.end();
  return success;
}

// ── Flush Offline Queue ──────────────────────────────────────────────────────
void flushOfflineQueue() {
  if (WiFi.status() != WL_CONNECTED) {
    return;
  }

  for (int i = 0; i < MAX_OFFLINE_EVENTS; i++) {
    if (eventQueue[i].active) {
      Serial.print(F("[Queue] Transmitting pending event in slot "));
      Serial.println(i);
      bool ok = transmitEvent(eventQueue[i].eventType, eventQueue[i].sequence, eventQueue[i].timestamp);
      if (ok) {
        clearQueueSlot(i);
        Serial.print(F("[Queue] Successfully acknowledged & cleared slot "));
        Serial.println(i);
      } else {
        // Stop flushing on error to preserve FIFO ordering
        Serial.println(F("[Queue] Retrying failed; holding remaining events."));
        break;
      }
    }
  }
}

// ── Debounced Sensor Readings ────────────────────────────────────────────────
void readDebouncedSensors() {
  int rawA = digitalRead(PIN_SENSOR_A);
  int rawB = digitalRead(PIN_SENSOR_B);
  unsigned long now = millis();

  if (rawA != lastReadingA) lastDebounceTimeA = now;
  if ((now - lastDebounceTimeA) > DEBOUNCE_MS) stableStateA = rawA;
  lastReadingA = rawA;

  if (rawB != lastReadingB) lastDebounceTimeB = now;
  if ((now - lastDebounceTimeB) > DEBOUNCE_MS) stableStateB = rawB;
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

  pinMode(PIN_SENSOR_A, INPUT_PULLUP);
  pinMode(PIN_SENSOR_B, INPUT_PULLUP);
  Serial.println(F("[GPIO] Sensor A (GPIO 26) configured."));
  Serial.println(F("[GPIO] Sensor B (GPIO 27) configured."));

  // Restore sequence from NVS
  preferences.begin("smartqueue", true);
  sequenceCounter = preferences.getULong("seq", 0);
  preferences.end();
  Serial.print(F("[NVS] Restored sequence counter: "));
  Serial.println(sequenceCounter);

  // Restore pending queue from NVS
  restoreQueueFromNVS();

  ensureWiFiConnected();
  configTime(GMT_OFFSET_SEC, DAYLIGHT_OFFSET_SEC, NTP_SERVER);

  // Watchdog timer (30 seconds)
  esp_task_wdt_config_t wdt_config = {
      .timeout_ms = WDT_TIMEOUT_SECONDS * 1000,
      .idle_core_mask = 0,
      .trigger_panic = true
  };
  esp_task_wdt_init(&wdt_config);
  esp_task_wdt_add(NULL);

  Serial.println(F("[System] Ready. Loop running."));
}

// ── Loop & Finite State Machine ──────────────────────────────────────────────
void loop() {
  esp_task_wdt_reset();
  readDebouncedSensors();
  unsigned long now = millis();

  bool activeA = (stableStateA == SENSOR_DETECTED_LEVEL);
  bool activeB = (stableStateB == SENSOR_DETECTED_LEVEL);

  switch (currentState) {
    case STATE_IDLE:
      if (activeA && !activeB) {
        currentState = STATE_A_TRIGGERED;
        triggerStartTime = now;
        Serial.println(F("[FSM] Sensor A triggered -> STATE_A_TRIGGERED"));
      } else if (activeB && !activeA) {
        currentState = STATE_B_TRIGGERED;
        triggerStartTime = now;
        Serial.println(F("[FSM] Sensor B triggered -> STATE_B_TRIGGERED"));
      } else if (activeA && activeB) {
        // Ambiguous simultaneous crossing: ignore
        Serial.println(F("[FSM] Ambiguous simultaneous crossing ignored."));
      }
      break;

    case STATE_A_TRIGGERED:
      if (activeB) {
        // Confirmed ENTRY sequence: A then B
        Serial.println(F("[FSM] Sensor B detected within window -> ENTRY CONFIRMED"));
        unsigned long nextSeq = loadNextSequence();
        String ts = getISOTimestamp();
        enqueueEvent("ENTRY", nextSeq, ts);
        flushOfflineQueue();
        currentState = STATE_WAIT_CLEAR;
      } else if (now - triggerStartTime > SEQUENCE_TIMEOUT_MS) {
        Serial.println(F("[FSM] Sequence timeout -> Resetting to IDLE"));
        currentState = STATE_WAIT_CLEAR;
      }
      break;

    case STATE_B_TRIGGERED:
      if (activeA) {
        // Confirmed EXIT sequence: B then A
        Serial.println(F("[FSM] Sensor A detected within window -> EXIT CONFIRMED"));
        unsigned long nextSeq = loadNextSequence();
        String ts = getISOTimestamp();
        enqueueEvent("EXIT", nextSeq, ts);
        flushOfflineQueue();
        currentState = STATE_WAIT_CLEAR;
      } else if (now - triggerStartTime > SEQUENCE_TIMEOUT_MS) {
        Serial.println(F("[FSM] Sequence timeout -> Resetting to IDLE"));
        currentState = STATE_WAIT_CLEAR;
      }
      break;

    case STATE_WAIT_CLEAR:
      if (!activeA && !activeB) {
        currentState = STATE_IDLE;
        Serial.println(F("[FSM] Sensors clear -> Ready (IDLE)"));
      }
      break;
  }

  // Periodic flush of pending offline events (every 5 seconds)
  if (now - lastRetryAttempt > 5000) {
    lastRetryAttempt = now;
    flushOfflineQueue();
  }

  delay(10);
}
