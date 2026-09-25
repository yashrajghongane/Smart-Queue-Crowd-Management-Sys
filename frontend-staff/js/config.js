/**
 * frontend-staff/js/config.js
 *
 * All configurable values for the staff frontend.
 */

const CONFIG = {
  // Base URL for all API calls.
  API_BASE_URL: window.CONFIG_API_BASE_URL || window.location.origin,

  // Hardcoded queue ID for demo purposes based on seed.py GM Queue
  DEFAULT_QUEUE_ID: "3d3f0f52-6b7a-4bb3-92cb-7f1f4d340301",
};

window.CONFIG = CONFIG;