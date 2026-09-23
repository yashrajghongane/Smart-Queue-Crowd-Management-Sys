/**
 * frontend-patient/js/status.js
 *
 * Token status page — polls GET /api/v1/visits/{visit_id}/status
 * and renders the current queue state for the patient.
 *
 * State rendering:
 *   WAITING   → show position in queue
 *   SERVING   → "You're being called! Please proceed."
 *   HOLD      → "Your token is on hold."
 *   SKIPPED   → "Your token was skipped."
 *   COMPLETED → "Your visit is complete."
 *
 * Polls every CONFIG.STATUS_POLL_INTERVAL_MS milliseconds.
 */

(function () {
  "use strict";

  const API_BASE    = window.CONFIG.API_BASE_URL;
  const POLL_MS     = window.CONFIG.STATUS_POLL_INTERVAL_MS;

  // ── DOM references ──────────────────────────────────────────────────────────
  const tokenNumberEl   = document.getElementById("token-number");
  const stateEl         = document.getElementById("token-state");
  const stateMessageEl  = document.getElementById("state-message");
  const patientsAheadEl = document.getElementById("patients-ahead");
  const servingTokenEl  = document.getElementById("serving-token");
  const lastUpdatedEl   = document.getElementById("last-updated");
  const errorBannerEl   = document.getElementById("error-banner");
  const loadingEl       = document.getElementById("loading");
  const contentEl       = document.getElementById("status-content");
  const refreshBtn      = document.getElementById("refresh-btn");
  const registerNewBtn  = document.getElementById("register-new-btn");

  // ── State ───────────────────────────────────────────────────────────────────
  let visitId       = sessionStorage.getItem("sq_visit_id");
  let pollTimer     = null;
  let isTerminal    = false;

  // ── State display config ────────────────────────────────────────────────────
  const STATE_CONFIG = {
    WAITING: {
      label:   "Waiting",
      message: "Please wait — we'll call your number soon.",
      color:   "text-yellow-700 bg-yellow-50 border-yellow-200",
      badge:   "bg-yellow-100 text-yellow-800",
    },
    SERVING: {
      label:   "Now Serving!",
      message: "Your turn! Please proceed to the counter / consultation room.",
      color:   "text-green-700 bg-green-50 border-green-200",
      badge:   "bg-green-100 text-green-800",
    },
    HOLD: {
      label:   "On Hold",
      message: "Your token is temporarily on hold. Please wait for staff to call you.",
      color:   "text-blue-700 bg-blue-50 border-blue-200",
      badge:   "bg-blue-100 text-blue-800",
    },
    SKIPPED: {
      label:   "Skipped",
      message: "Your token was marked as skipped. Please speak to the reception staff.",
      color:   "text-orange-700 bg-orange-50 border-orange-200",
      badge:   "bg-orange-100 text-orange-800",
    },
    COMPLETED: {
      label:   "Completed",
      message: "Your visit is complete. Thank you!",
      color:   "text-gray-700 bg-gray-50 border-gray-200",
      badge:   "bg-gray-100 text-gray-700",
    },
  };

  const TERMINAL_STATES = new Set(["COMPLETED", "SKIPPED"]);

  // ── Fetch and render ────────────────────────────────────────────────────────
  async function fetchStatus() {
    if (!visitId) {
      showError("No visit ID found. Please register again.", true);
      return;
    }

    clearError();

    try {
      const response = await fetch(
        `${API_BASE}/api/v1/visits/${encodeURIComponent(visitId)}/status`
      );

      if (response.status === 404) {
        showError("Visit not found. Please register again.", true);
        stopPolling();
        return;
      }

      if (!response.ok) {
        showError("Could not load your status. Retrying…", false);
        return;
      }

      const data = await response.json();
      renderStatus(data);

      if (TERMINAL_STATES.has(data.state)) {
        isTerminal = true;
        stopPolling();
      }

    } catch (err) {
      console.error("Status fetch error:", err);
      showError("Connection problem. Retrying…", false);
    }
  }

  function renderStatus(data) {
    const cfg = STATE_CONFIG[data.state] || {
      label:   data.state,
      message: "",
      color:   "text-gray-700 bg-gray-50 border-gray-200",
      badge:   "bg-gray-100 text-gray-700",
    };

    // Token number
    tokenNumberEl.textContent = data.token_number;

    // State badge
    stateEl.textContent  = cfg.label;
    stateEl.className    = `inline-block px-3 py-1 rounded-full text-sm font-semibold ${cfg.badge}`;

    // Message box
    stateMessageEl.textContent = cfg.message;
    stateMessageEl.className   = `rounded-lg p-4 border text-sm ${cfg.color}`;

    // Patients ahead
    if (data.state === "WAITING") {
      patientsAheadEl.parentElement.classList.remove("hidden");
      if (data.patients_ahead === 0) {
        patientsAheadEl.textContent = "You're next!";
        patientsAheadEl.className = "text-2xl font-bold text-green-600";
      } else {
        patientsAheadEl.textContent = data.patients_ahead;
        patientsAheadEl.className = "text-2xl font-bold text-gray-800";
      }
    } else {
      patientsAheadEl.parentElement.classList.add("hidden");
    }

    // Currently serving
    if (data.serving_token) {
      servingTokenEl.parentElement.classList.remove("hidden");
      servingTokenEl.textContent = data.serving_token;
    } else {
      servingTokenEl.parentElement.classList.add("hidden");
    }

    // Last updated
    lastUpdatedEl.textContent = new Date(data.updated_at).toLocaleTimeString();

    // Show content, hide loading
    loadingEl.classList.add("hidden");
    contentEl.classList.remove("hidden");

    // Disable auto-refresh button for terminal states
    if (isTerminal) {
      refreshBtn.textContent = "Visit Complete";
      refreshBtn.disabled = true;
      refreshBtn.className = refreshBtn.className.replace("bg-indigo-600 hover:bg-indigo-700", "bg-gray-400 cursor-not-allowed");
    }
  }

  // ── Polling ─────────────────────────────────────────────────────────────────
  function startPolling() {
    if (pollTimer) return;
    pollTimer = setInterval(fetchStatus, POLL_MS);
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  // ── Error handling ──────────────────────────────────────────────────────────
  function showError(message, fatal) {
    errorBannerEl.textContent = message;
    errorBannerEl.classList.remove("hidden");
    if (fatal) {
      stopPolling();
      loadingEl.classList.add("hidden");
      registerNewBtn.classList.remove("hidden");
    }
  }

  function clearError() {
    errorBannerEl.textContent = "";
    errorBannerEl.classList.add("hidden");
  }

  // ── Event listeners ─────────────────────────────────────────────────────────
  refreshBtn.addEventListener("click", () => {
    if (!isTerminal) fetchStatus();
  });

  registerNewBtn.addEventListener("click", () => {
    sessionStorage.clear();
    window.location.href = "index.html";
  });

  // ── Init ────────────────────────────────────────────────────────────────────
  if (!visitId) {
    showError("No registration found. Please scan the QR code or register again.", true);
  } else {
    fetchStatus();
    startPolling();
  }

})();
