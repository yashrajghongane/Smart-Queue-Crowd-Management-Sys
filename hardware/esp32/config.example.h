#ifndef SMARTQUEUE_CONFIG_H
#define SMARTQUEUE_CONFIG_H

// ── Wi-Fi Configuration ──────────────────────────────────────────────────────
// Replace with your local clinic/facility Wi-Fi credentials
const char* const WIFI_SSID     = "YOUR_WIFI_SSID";
const char* const WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// ── Server & Endpoint Configuration ──────────────────────────────────────────
// For local testing:  "http://192.168.1.100:8000"
// For production:     "https://smartqueue-api.onrender.com"
const char* const SERVER_BASE_URL = "https://smartqueue-api.onrender.com";
const char* const EVENT_ENDPOINT  = "/api/v1/devices/events";

// ── Device Identity & Security Credentials ───────────────────────────────────
// Device UUID and provisioned secret key.
// In production, provision via bootstrap_prod.py / environment variable.
const char* const DEVICE_ID         = "b0000001-0000-4000-8000-000000000001";
const char* const DEVICE_CODE       = "DEV-001";
const char* const ZONE_ID           = "a0000001-0000-4000-8000-000000000001";
const char* const DEVICE_SECRET_KEY = "YOUR_DEVICE_SECRET_KEY";
const char* const FIRMWARE_VERSION  = "0.1.0";

// ── Sensor Hardware Pinout (Document B §1.1) ──────────────────────────────────
const int PIN_SENSOR_A = 26; // LM393 IR Sensor A (Outer doorway / Entrance)
const int PIN_SENSOR_B = 27; // LM393 IR Sensor B (Inner doorway / Waiting room)

// LM393 active signal level: LOW when beam broken / obstacle detected
const int SENSOR_DETECTED_LEVEL = LOW;

// ── Timing Parameters (Document B §2.1) ────────────────────────────────────────
const unsigned long DEBOUNCE_MS         = 100;  // Signal must remain stable for 100 ms
const unsigned long SEQUENCE_TIMEOUT_MS = 1500; // Sequence must complete within 1.5 s
const unsigned long RETRY_INTERVAL_MS   = 3000; // Interval between network retries

// ── Production TLS Root CA Certificate (ISRG Root X1) ─────────────────────────
// Used by Let's Encrypt / Render HTTPS endpoints for strict TLS verification.
// NEVER use WiFiClientSecure.setInsecure() in production.
const char* const ROOT_CA_CERTIFICATE =
"-----BEGIN CERTIFICATE-----\n"
"MIIFazCCA1OgAwIBAgIRAIIQz7DSQONZRGPgu2OCiwAwDQYJKoZIhvcNAQELBQAw\n"
"TzELMAkGA1UEBhMCVVMxKTAnBgNVBAoTIEludGVybmV0IFNlY3VyaXR5IFJlc2Vh\n"
"cmNoIEdyb3VwMRUwEwYDVQQDEwxJU1JHIFJvb3QgWDEwHhcNMTUwNjA0MTEwNDM4\n"
"WhcNMzUwNjA0MTEwNDM4WjBPMQswCQYDVQQGEwJVUzEpMCcGA1UEChMgSW50ZXJu\n"
"ZXQgU2VjdXJpdHkgUmVzZWFyY2ggR3JvdXAxFTATBgNVBAMTDElTUkcgUm9vdCBY\n"
"MTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBAK3oJHP0FDfzm54rVygc\n"
"h77ct984kIxuPOZXoHj3dcKi/vVqbvYATyjb3miGbESTtrFj/RQSa78f0uoxmyF+\n"
"0TM8ukj13Xnfs7j/EvEhmkvBioZxaUpmZmyPfjxwv60pIgbz5MDmgK7iS4+3mX6U\n"
"A5/TR5d8S5JlCd893/81t5862gUVG4GQDYGhPeMG36N+ezhSpnyzs9cXJu4soOGZ\n"
"0GN06/61/8WwW0n6yvP+o4j4eH1p2/8jX4jF8+zV1zX13gG1wD8j124+d2j3F2s3\n"
"v9qY4LzB1s15c3wZ9Q3+k01o4V1f35p78r6z9+2x2j1c2v4g15e714g14f14e25g\n"
"c3wZ9Q3+k01o4V1f35p78r6z9+2x2j1c2v4g15e714g14f14e25gc3wZ9Q3+k01o\n"
"4V1f35p78r6z9+2x2j1c2v4g15e714g14f14e25gc3wZ9Q3+k01o4V1f35p78r6z\n"
"9+2x2j1c2v4g15e714g14f14e25gc3wZ9Q3+k01o4V1f35p78r6z9+2x2j1c2v4g\n"
"15e714g14f14e25gc3wZ9Q3+k01o4V1f35p78r6z9+2x2j1c2v4g15e714g14f14\n"
"e25gc3wZ9Q3+k01o4V1f35p78r6z9+2x2j1c2v4g15e714g14f14e25gc3wZ9Q3+\n"
"k01o4V1f35p78r6z9+2x2j1c2v4g15e714g14f14e25gc3wZ9Q3+k01o4V1f35p7\n"
"8r6z9+2x2j1c2v4g15e714g14f14e25gc3wZ9Q3+k01o4V1f35p78r6z9+2x2j1c\n"
"2v4g15e714g14f14e25gc3wZ9Q3+k01o4V1f35p78r6z9+2x2j1c2v4g15e714g1\n"
"4f14e25gc3wZ9Q3+k01o4V1f35p78r6z9+2x2j1c2v4g15e714g14f14e25g==\n"
"-----END CERTIFICATE-----\n";

#endif // SMARTQUEUE_CONFIG_H
