/**
 * frontend-patient/js/config.js
 *
 * All configurable values for the patient frontend.
 *
 * In development the patient app is served by the same FastAPI server,
 * so window.location.origin is the correct API base.
 *
 * For production deployment, override API_BASE_URL to point at your
 * hosted backend domain, e.g. "https://api.yourapp.com"
 */

const CONFIG = {
  // Base URL for all API calls.
  // Change this when deploying the patient frontend to a separate host.
  API_BASE_URL: window.location.origin,

  // How often (ms) the status page polls the backend for updates.
  STATUS_POLL_INTERVAL_MS: 10000,
};

// Make config available globally — no module bundler needed.
window.CONFIG = CONFIG;
