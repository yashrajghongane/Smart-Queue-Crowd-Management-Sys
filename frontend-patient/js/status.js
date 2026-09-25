/**
 * frontend-patient/js/status.js
 *
 * Token status page — polls GET /api/v1/visits/{visit_id}/status
 * and renders the current queue state for the patient.
 *
 * State rendering:
 *   WAITING   → show position in queue + patients ahead count
 *   SERVING   → "It's your turn! Please proceed."
 *   HOLD      → "Your token is temporarily on hold."
 *   SKIPPED   → "Your token was skipped. Please speak to reception."
 *   COMPLETED → "Your visit is complete."
 *
 * Polls every CONFIG.STATUS_POLL_INTERVAL_MS milliseconds.
 * Stops polling on terminal states (COMPLETED, SKIPPED).
 * Detects and reports browser offline state.
 */

(function () {
  "use strict";

  const API_BASE = window.CONFIG.API_BASE_URL;
  const POLL_MS  = window.CONFIG.STATUS_POLL_INTERVAL_MS;

  // ── DOM references ──────────────────────────────────────────────────────────
  const tokenNumberEl       = document.getElementById("token-number");
  const queueNameEl         = document.getElementById("queue-name");
  const stateEl             = document.getElementById("token-state");
  const stateMessageEl      = document.getElementById("state-message");
  const patientsAheadSection = document.getElementById("patients-ahead-section");
  const patientsAheadEl     = document.getElementById("patients-ahead");
  const patientsAheadLabel  = document.getElementById("patients-ahead-label");
  const estimatedWaitSection = document.getElementById("estimated-wait-section");
  const estimatedWaitEl     = document.getElementById("estimated-wait");
  const servingSection      = document.getElementById("serving-token-section");
  const servingTokenEl      = document.getElementById("serving-token");
  const lastUpdatedEl       = document.getElementById("last-updated");
  const errorBannerEl       = document.getElementById("error-banner");
  const errorTextEl         = document.getElementById("error-text");
  const loadingEl           = document.getElementById("loading");
  const contentEl           = document.getElementById("status-content");
  const refreshBtn          = document.getElementById("refresh-btn");
  const registerNewBtn      = document.getElementById("register-new-btn");
  const offlineBannerEl     = document.getElementById("offline-banner");

  // ── State ───────────────────────────────────────────────────────────────────
  let visitId    = sessionStorage.getItem("sq_visit_id");
  let pollTimer  = null;
  let isTerminal = false;

  // ── State display config ────────────────────────────────────────────────────
  const STATE_CONFIG = {
    WAITING: {
      label:   "Waiting",
      message: "Please take a seat. We'll call your number soon.",
      color:   "text-amber-700 bg-amber-50 border-amber-200",
      badge:   "bg-amber-100 text-amber-800",
      icon:    '<svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>',
    },
    SERVING: {
      label:   "Now Serving",
      message: "It's your turn! Please proceed to the consultation room.",
      color:   "text-emerald-700 bg-emerald-50 border-emerald-200",
      badge:   "bg-emerald-100 text-emerald-800",
      icon:    '<svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>',
    },
    HOLD: {
      label:   "On Hold",
      message: "Your token is temporarily on hold. Staff will assist you shortly.",
      color:   "text-blue-700 bg-blue-50 border-blue-200",
      badge:   "bg-blue-100 text-blue-800",
      icon:    '<svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>',
    },
    SKIPPED: {
      label:   "Skipped",
      message: "Your token was marked as skipped. Please speak to the reception staff.",
      color:   "text-rose-700 bg-rose-50 border-rose-200",
      badge:   "bg-rose-100 text-rose-800",
      icon:    '<svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>',
    },
    COMPLETED: {
      label:   "Completed",
      message: "Your visit is complete. Wishing you good health!",
      color:   "text-slate-700 bg-slate-100 border-slate-300",
      badge:   "bg-slate-200 text-slate-700",
      icon:    '<svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>',
    },
  };

  const TERMINAL_STATES = new Set(["COMPLETED", "SKIPPED"]);

  // ── Offline detection ────────────────────────────────────────────────────────
  function updateOnlineStatus() {
    if (offlineBannerEl) {
      if (!navigator.onLine) {
        offlineBannerEl.classList.remove("hidden");
        stopPolling();
      } else {
        offlineBannerEl.classList.add("hidden");
        if (!isTerminal && visitId) startPolling();
      }
    }
  }
  window.addEventListener("online",  updateOnlineStatus);
  window.addEventListener("offline", updateOnlineStatus);

  // ── Fetch and render ────────────────────────────────────────────────────────
  async function fetchStatus() {
    if (!visitId) {
      showError("No visit ID found. Please register again.", true);
      return;
    }

    if (!navigator.onLine) return;  // Don't attempt while offline

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
        showError(`Could not load your status (${response.status}). Retrying…`, false);
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
      icon:    "",
    };

    // Queue Name
    if (queueNameEl) {
      queueNameEl.textContent = data.queue_name || "General Medicine Queue";
    }

    // Token number
    tokenNumberEl.textContent = data.token_number;

    // State badge
    stateEl.textContent = cfg.label;
    stateEl.className   = `inline-block px-4 py-1.5 rounded-full text-base font-bold uppercase tracking-wide shadow-sm ${cfg.badge}`;

    // Message box
    stateMessageEl.innerHTML = `${cfg.icon} <span>${cfg.message}</span>`;
    stateMessageEl.className = `rounded-2xl p-5 border text-base font-medium text-center shadow-sm flex items-center justify-center gap-2 ${cfg.color}`;

    // Patients ahead & Estimated wait — only shown for WAITING state
    if (data.state === "WAITING") {
      patientsAheadSection.classList.remove("hidden");
      if (estimatedWaitSection) estimatedWaitSection.classList.remove("hidden");

      if (data.patients_ahead === 0) {
        // "You're next!" — update both label and value clearly
        if (patientsAheadLabel) patientsAheadLabel.textContent = "Position";
        patientsAheadEl.textContent = "You're next!";
        patientsAheadEl.className   = "text-2xl font-extrabold text-emerald-600";
        if (estimatedWaitEl) estimatedWaitEl.textContent = "< 5 mins";
      } else {
        if (patientsAheadLabel) patientsAheadLabel.textContent = "Patients Ahead";
        patientsAheadEl.textContent = data.patients_ahead;
        patientsAheadEl.className   = "text-4xl font-extrabold text-slate-800";
        const waitMins = data.estimated_wait_minutes !== undefined ? data.estimated_wait_minutes : (data.patients_ahead * 5);
        if (estimatedWaitEl) estimatedWaitEl.textContent = `~${waitMins} mins`;
      }
    } else {
      patientsAheadSection.classList.add("hidden");
      if (estimatedWaitSection) estimatedWaitSection.classList.add("hidden");
    }

    // Currently serving — only shown when a token is actively being served
    if (data.serving_token) {
      servingSection.classList.remove("hidden");
      servingTokenEl.textContent = data.serving_token;
    } else {
      servingSection.classList.add("hidden");
    }

    // Last updated — local time, 24h format
    lastUpdatedEl.textContent = new Date(data.updated_at).toLocaleTimeString([], {
      hour: "2-digit", minute: "2-digit", second: "2-digit",
    });

    // Show content, hide spinner
    loadingEl.classList.add("hidden");
    contentEl.classList.remove("hidden");

    // Announce the state change for screen readers (aria-live region updates)
    // The aria-live="polite" attribute on contentEl handles this automatically.

    // Terminal state — disable refresh button
    if (isTerminal) {
      refreshBtn.innerHTML = `
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
        </svg>
        Visit Complete`;
      refreshBtn.disabled  = true;
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
    // Use the inner <span> to avoid clearing the SVG icon in the banner
    if (errorTextEl) {
      errorTextEl.textContent = message;
    } else {
      // Fallback if HTML doesn't have the inner span pattern
      errorBannerEl.textContent = message;
    }
    errorBannerEl.classList.remove("hidden");
    if (fatal) {
      stopPolling();
      loadingEl.classList.add("hidden");
      registerNewBtn.classList.remove("hidden");
    }
  }

  function clearError() {
    if (errorTextEl) errorTextEl.textContent = "";
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
    loadingEl.classList.add("hidden");
  } else {
    updateOnlineStatus();
    fetchStatus();
    if (!isTerminal) startPolling();
  }

})();
