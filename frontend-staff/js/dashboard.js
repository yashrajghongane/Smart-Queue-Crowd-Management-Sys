(function () {
  "use strict";

  const API_BASE = window.CONFIG.API_BASE_URL;
  const QUEUE_ID = window.CONFIG.DEFAULT_QUEUE_ID;
  const ZONE_ID  = window.CONFIG.DEFAULT_ZONE_ID || "a0000001-0000-4000-8000-000000000001";
  const QUEUE_POLL_MS = window.CONFIG.STATUS_POLL_INTERVAL_MS || 5000;
  const CROWD_POLL_MS = window.CONFIG.CROWD_POLL_INTERVAL_MS || 5000;

  // ── DOM References: Queue ──────────────────────────────────────────────────
  const servingEl = document.getElementById("serving-token");
  const waitingEl = document.getElementById("waiting-count");
  const messageEl = document.getElementById("status-message");
  const refreshEl = document.getElementById("queue-refresh-state");
  const recallInput = document.getElementById("recall-token-input");
  const btnRecallCustom = document.getElementById("btn-recall-custom");

  const buttons = {
    call: document.getElementById("btn-call-next"),
    hold: document.getElementById("btn-hold"),
    recall: document.getElementById("btn-recall"),
    skip: document.getElementById("btn-skip"),
    complete: document.getElementById("btn-complete"),
  };

  // ── DOM References: Crowd ──────────────────────────────────────────────────
  const crowdRefreshEl = document.getElementById("crowd-refresh-state");
  const occCountEl = document.getElementById("occupancy-count");
  const capMaxEl = document.getElementById("capacity-max");
  const capBadgeEl = document.getElementById("capacity-badge");
  const utilBarEl = document.getElementById("utilization-bar");
  const utilTextEl = document.getElementById("utilization-text");
  const entriesEl = document.getElementById("entries-today");
  const exitsEl = document.getElementById("exits-today");
  const netChangeEl = document.getElementById("net-change");
  const staleWarningEl = document.getElementById("stale-warning");
  const devBadgeEl = document.getElementById("device-status-badge");
  const devCodeEl = document.getElementById("device-code");
  const fwVerEl = document.getElementById("firmware-version");
  const lastSeqEl = document.getElementById("last-sequence");
  const lastSeenEl = document.getElementById("last-seen");

  // ── DOM References: Auth ───────────────────────────────────────────────────
  const btnLoginToggle = document.getElementById("btn-login-toggle");
  const loginModal = document.getElementById("login-modal");
  const btnCloseLogin = document.getElementById("btn-close-login");
  const loginForm = document.getElementById("login-form");
  const loginUserEl = document.getElementById("login-username");
  const loginPassEl = document.getElementById("login-password");
  const loginErrorEl = document.getElementById("login-error");
  const userDisplayEl = document.getElementById("user-display");
  const roleBadgeEl = document.getElementById("role-badge");

  let servingTokenId = null;
  let lastActionTokenId = null;
  let authToken = localStorage.getItem("sq_staff_token") || null;

  // ── Auth Helpers ───────────────────────────────────────────────────────────
  function getAuthHeaders() {
    const headers = { "Content-Type": "application/json" };
    if (authToken) {
      headers["Authorization"] = `Bearer ${authToken}`;
    }
    return headers;
  }

  function updateAuthUI() {
    const userJson = localStorage.getItem("sq_staff_user");
    if (authToken && userJson) {
      try {
        const user = JSON.parse(userJson);
        userDisplayEl.textContent = user.display_name || user.username;
        userDisplayEl.classList.remove("hidden");
        roleBadgeEl.textContent = user.role;
        btnLoginToggle.textContent = "Logout";
      } catch (e) {
        userDisplayEl.classList.add("hidden");
        btnLoginToggle.textContent = "Login";
      }
    } else {
      userDisplayEl.classList.add("hidden");
      btnLoginToggle.textContent = "Login";
    }
  }

  btnLoginToggle.addEventListener("click", () => {
    if (authToken) {
      // Logout
      authToken = null;
      localStorage.removeItem("sq_staff_token");
      localStorage.removeItem("sq_staff_user");
      updateAuthUI();
      message("Logged out successfully.", "info");
    } else {
      loginModal.classList.remove("hidden");
    }
  });

  btnCloseLogin.addEventListener("click", () => {
    loginModal.classList.add("hidden");
  });

  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    loginErrorEl.classList.add("hidden");
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: loginUserEl.value.trim(),
          password: loginPassEl.value,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        loginErrorEl.textContent = data.detail || "Authentication failed.";
        loginErrorEl.classList.remove("hidden");
        return;
      }
      authToken = data.access_token;
      localStorage.setItem("sq_staff_token", authToken);
      localStorage.setItem("sq_staff_user", JSON.stringify(data));
      loginModal.classList.add("hidden");
      updateAuthUI();
      message(`Logged in as ${data.display_name} (${data.role}).`, "success");
      await Promise.all([loadQueue(), loadCrowd()]);
    } catch (err) {
      loginErrorEl.textContent = "Network error during login.";
      loginErrorEl.classList.remove("hidden");
    }
  });

  // ── UI Messages ────────────────────────────────────────────────────────────
  function message(text, type = "info") {
    messageEl.textContent = text;
    messageEl.className = "rounded-xl border p-4 text-sm font-medium " + ({
      error: "bg-red-50 text-red-700 border-red-200",
      success: "bg-emerald-50 text-emerald-700 border-emerald-200",
      info: "bg-blue-50 text-blue-700 border-blue-200",
    }[type] || "bg-blue-50 text-blue-700 border-blue-200");
    messageEl.classList.remove("hidden");
  }

  function clearMessage() {
    messageEl.textContent = "";
    messageEl.classList.add("hidden");
  }

  function setBusy(busy) {
    if (buttons.call) buttons.call.disabled = busy;
    if (buttons.hold) buttons.hold.disabled = busy || !servingTokenId;
    if (buttons.skip) buttons.skip.disabled = busy || !servingTokenId;
    if (buttons.complete) buttons.complete.disabled = busy || !servingTokenId;
    if (buttons.recall) buttons.recall.disabled = busy;
    if (btnRecallCustom) btnRecallCustom.disabled = busy;
  }

  // ── Queue Loading ──────────────────────────────────────────────────────────
  async function loadQueue() {
    try {
      refreshEl.textContent = "Syncing…";
      const res = await fetch(`${API_BASE}/api/v1/queues/${encodeURIComponent(QUEUE_ID)}`, {
        headers: getAuthHeaders(),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not load queue");
      servingEl.textContent = data.serving_token || "—";
      waitingEl.textContent = String(data.waiting_count ?? 0);
      servingTokenId = data.serving_token_id || null;
      setBusy(false);
      refreshEl.textContent = "Live";
    } catch (err) {
      setBusy(false);
      refreshEl.textContent = "Failed";
    }
  }

  // ── Crowd Loading ──────────────────────────────────────────────────────────
  async function loadCrowd() {
    try {
      if (crowdRefreshEl) crowdRefreshEl.textContent = "Syncing…";
      const res = await fetch(`${API_BASE}/api/v1/zones/${encodeURIComponent(ZONE_ID)}/crowd`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) return;
      const data = await res.json();

      // Occupancy & Capacity
      occCountEl.textContent = String(data.occupancy ?? 0);
      capMaxEl.textContent = `/ ${data.capacity ?? 10} capacity`;

      // Utilization bar & text
      const util = data.utilization_percent ?? 0;
      utilBarEl.style.width = `${Math.min(util, 100)}%`;
      utilTextEl.textContent = `${util}% utilization`;

      // Capacity alert badge
      const alert = data.capacity_alert || "NORMAL";
      capBadgeEl.textContent = alert;
      const alertColors = {
        NORMAL: "bg-emerald-100 text-emerald-800",
        MODERATE: "bg-amber-100 text-amber-800",
        HIGH: "bg-orange-100 text-orange-800",
        CRITICAL: "bg-rose-100 text-rose-800 font-black animate-pulse",
      };
      capBadgeEl.className = `rounded-full px-2.5 py-0.5 text-xs font-bold ${alertColors[alert] || alertColors.NORMAL}`;

      // Utilization bar color
      if (alert === "CRITICAL") utilBarEl.className = "bg-rose-600 h-2 rounded-full transition-all duration-500";
      else if (alert === "HIGH") utilBarEl.className = "bg-orange-500 h-2 rounded-full transition-all duration-500";
      else if (alert === "MODERATE") utilBarEl.className = "bg-amber-500 h-2 rounded-full transition-all duration-500";
      else utilBarEl.className = "bg-emerald-600 h-2 rounded-full transition-all duration-500";

      // Traffic
      entriesEl.textContent = String(data.entries_today ?? 0);
      exitsEl.textContent = String(data.exits_today ?? 0);
      netChangeEl.textContent = String(data.net_change_today ?? 0);

      // Hardware status
      devCodeEl.textContent = data.device_code || "DEV-001";
      fwVerEl.textContent = data.firmware_version || "0.1.0";
      lastSeqEl.textContent = data.last_sequence ? `#${data.last_sequence}` : "—";
      lastSeenEl.textContent = data.last_seen_at
        ? new Date(data.last_seen_at).toLocaleTimeString()
        : "—";

      const devStatus = data.device_status || "OFFLINE";
      devBadgeEl.textContent = devStatus;
      if (devStatus === "ONLINE") {
        devBadgeEl.className = "rounded-full bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5";
        staleWarningEl.classList.add("hidden");
      } else if (devStatus === "STALE") {
        devBadgeEl.className = "rounded-full bg-amber-100 text-amber-800 font-bold px-2 py-0.5";
        staleWarningEl.classList.remove("hidden");
      } else {
        devBadgeEl.className = "rounded-full bg-slate-200 text-slate-700 px-2 py-0.5";
        staleWarningEl.classList.add("hidden");
      }

      if (crowdRefreshEl) crowdRefreshEl.textContent = "Live";
    } catch (err) {
      if (crowdRefreshEl) crowdRefreshEl.textContent = "Failed";
    }
  }

  // ── Queue Actions ──────────────────────────────────────────────────────────
  async function action(path, body, success) {
    clearMessage();
    setBusy(true);
    try {
      const res = await fetch(API_BASE + path, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify(body || {}),
      });
      const data = await res.json();
      if (!res.ok) {
        const detail = typeof data.detail === "string" ? data.detail : (data.detail?.message || data.message || "Action failed");
        throw new Error(detail);
      }
      message(success, "success");
      await loadQueue();
    } catch (err) {
      message(err.message || "Action failed.", "error");
      setBusy(false);
    }
  }

  buttons.call.addEventListener("click", () =>
    action(`/api/v1/queues/${QUEUE_ID}/call-next`, {}, "Next patient called.")
  );

  buttons.hold.addEventListener("click", () => {
    if (servingTokenId) {
      lastActionTokenId = servingTokenId;
      if (recallInput) recallInput.value = lastActionTokenId;
      action(`/api/v1/tokens/${servingTokenId}/hold`, { reason: "Staff hold" }, "Token placed on hold.");
    }
  });

  buttons.skip.addEventListener("click", () => {
    if (servingTokenId) {
      lastActionTokenId = servingTokenId;
      if (recallInput) recallInput.value = lastActionTokenId;
      action(`/api/v1/tokens/${servingTokenId}/skip`, { reason: "No show" }, "Token skipped.");
    }
  });

  buttons.complete.addEventListener("click", () => {
    if (servingTokenId) {
      action(`/api/v1/tokens/${servingTokenId}/complete`, {}, "Consultation completed.");
    }
  });

  function handleRecall() {
    const customId = recallInput ? recallInput.value.trim() : "";
    const targetTokenId = customId || servingTokenId || lastActionTokenId;
    if (!targetTokenId) {
      message("Enter a token UUID or hold/skip a token first to recall.", "error");
      return;
    }
    action(`/api/v1/tokens/${targetTokenId}/recall`, {}, "Token recalled to WAITING.");
  }

  buttons.recall.addEventListener("click", handleRecall);
  if (btnRecallCustom) btnRecallCustom.addEventListener("click", handleRecall);

  // ── Initialize ─────────────────────────────────────────────────────────────
  updateAuthUI();
  loadQueue();
  loadCrowd();
  setInterval(loadQueue, QUEUE_POLL_MS);
  setInterval(loadCrowd, CROWD_POLL_MS);

})();