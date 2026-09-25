#ifndef SMARTQUEUE_CONFIG_H
#define SMARTQUEUE_CONFIG_H

// ── Wi-Fi Configuration ──────────────────────────────────────────────────────
const char* const WIFI_SSID     = "Your_WiFi_SSID";
const char* const WIFI_PASSWORD = "Your_WiFi_Password";

// ── Server & Endpoint Configuration ──────────────────────────────────────────
// For local laptop run, use laptop's LAN IP e.g. "http://192.168.1.100:8000"
// For production, use "https://api.yourdomain.com"
const char* const SERVER_BASE_URL = "http://192.168.1.100:8000";
const char* const EVENT_ENDPOINT  = "/api/v1/devices/events";

// ── Device Identity & Security Credentials ───────────────────────────────────
// Matches database seed: DEV-001 linked to General OPD Waiting Area
const char* const DEVICE_ID         = "devi-0001-0000-0000-0000-000000000001";
const char* const DEVICE_CODE       = "DEV-001";
const char* const ZONE_ID           = "zone-0001-0000-0000-0000-000000000001";
const char* const DEVICE_SECRET_KEY = "esp32-secret-key-001";
const char* const FIRMWARE_VERSION  = "0.1.0";

// ── Sensor Hardware Pinout (Document B §1.1) ──────────────────────────────────
const int PIN_SENSOR_A = 26; // LM393 IR Sensor A (Outer / Entrance side)
const int PIN_SENSOR_B = 27; // LM393 IR Sensor B (Inner / Room side)

// LM393 active signal level: LOW when beam broken / obstacle detected
const int SENSOR_DETECTED_LEVEL = LOW;

// ── Timing Parameters (Document B §2.1) ────────────────────────────────────────
const unsigned long DEBOUNCE_MS       = 100;  // Signal must remain stable for 100 ms
const unsigned long SEQUENCE_TIMEOUT_MS = 1500; // Sequence must complete within 1.5 seconds
const unsigned long RETRY_INTERVAL_MS = 3000; // Interval between network retries

#endif // SMARTQUEUE_CONFIG_H
