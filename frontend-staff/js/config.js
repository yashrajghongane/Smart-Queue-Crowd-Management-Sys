const CONFIG = {
  API_BASE_URL: window.CONFIG_API_BASE_URL || window.location.origin,
  DEFAULT_QUEUE_ID: window.DEFAULT_QUEUE_ID || "3d3f0f52-6b7a-4bb3-92cb-7f1f4d340301",
  STATUS_POLL_INTERVAL_MS: 5000,
};
window.CONFIG = CONFIG;