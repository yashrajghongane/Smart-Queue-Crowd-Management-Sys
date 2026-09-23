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
      message: "Please take a seat. We'll call your number soon.",
      color:   "text-amber-700 bg-amber-50 border-amber-200",
      badge:   "bg-amber-100 text-amber-800",
      icon:    `<svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`
    },
    SERVING: {
      label:   "Now Serving",
      message: "It's your turn! Please proceed to the consultation room.",
      color:   "text-emerald-700 bg-emerald-50 border-emerald-200",
      badge:   "bg-emerald-100 text-emerald-800",
      icon:    `<svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`
    },
    HOLD: {
      label:   "On Hold",
      message: "Your token is temporarily on hold. Staff will assist you shortly.",
      color:   "text-blue-700 bg-blue-50 border-blue-200",
      badge:   "bg-blue-100 text-blue-800",
      icon:    `<svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`
    },
    SKIPPED: {
      label:   "Skipped",
      message: "Your token was marked as skipped. Please speak to the reception.",
      color:   "text-rose-700 bg-rose-50 border-rose-200",
      badge:   "bg-rose-100 text-rose-800",
      icon:    `<svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`
    },
    COMPLETED: {
      label:   "Completed",
      message: "Your visit is complete. Wishing you good health!",
      color:   "text-slate-700 bg-slate-100 border-slate-300",
      badge:   "bg-slate-200 text-slate-700",
      icon:    `<svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>`
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
      color:   "text-slate-700 bg-slate-50 border-slate-200",
      badge:   "bg-slate-100 text-slate-700",
      icon:    ""
    };

    // Token number
    tokenNumberEl.textContent = data.token_number;

    // State badge
    stateEl.textContent  = cfg.label;
    stateEl.className    = `inline-block px-4 py-1.5 rounded-full text-base font-bold uppercase tracking-wide shadow-sm ${cfg.badge}`;

    // Message box
    stateMessageEl.innerHTML = `${cfg.icon} <span>${cfg.message}</span>`;
    stateMessageEl.className   = `rounded-2xl p-5 border text-base font-medium text-center shadow-sm flex items-center justify-center gap-2 ${cfg.color}`;

    // Patients ahead
    if (data.state === "WAITING") {
      patientsAheadEl.parentElement.classList.remove("hidden");
      if (data.patients_ahead === 0) {
        patientsAheadEl.textContent = "You're next!";
        patientsAheadEl.className = "text-3xl font-extrabold text-emerald-600";
      } else {
        patientsAheadEl.textContent = data.patients_ahead;
        patientsAheadEl.className = "text-4xl font-extrabold text-slate-800";
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
    lastUpdatedEl.textContent = new Date(data.updated_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});

    // Show content, hide loading
    loadingEl.classList.add("hidden");
    contentEl.classList.remove("hidden");

    // Disable auto-refresh button for terminal states
    if (isTerminal) {
      refreshBtn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg> Visit Complete`;
      refreshBtn.disabled = true;
      refreshBtn.className = "w-full sm:w-auto text-sm bg-slate-100 border border-slate-200 text-slate-400 px-5 py-2.5 rounded-xl font-bold cursor-not-allowed flex items-center justify-center gap-2";
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
    errorBannerEl.querySelector("span").textContent = message;
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
