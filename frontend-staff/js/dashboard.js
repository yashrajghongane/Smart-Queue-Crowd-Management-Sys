(function () {
  "use strict";
  const API_BASE = window.CONFIG.API_BASE_URL;
  const QUEUE_ID = window.CONFIG.DEFAULT_QUEUE_ID;
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
  let servingTokenId = null;
  let lastActionTokenId = null;

  function message(text, type="info") {
    messageEl.textContent = text;
    messageEl.className = "rounded-xl border p-4 text-sm font-medium " + ({
      error: "bg-red-50 text-red-700 border-red-200",
      success: "bg-emerald-50 text-emerald-700 border-emerald-200",
      info: "bg-blue-50 text-blue-700 border-blue-200",
    }[type] || "bg-blue-50 text-blue-700 border-blue-200");
    messageEl.classList.remove("hidden");
  }
  function clearMessage() { messageEl.textContent = ""; messageEl.classList.add("hidden"); }
  function setBusy(busy) {
    if (buttons.call) buttons.call.disabled = busy;
    if (buttons.hold) buttons.hold.disabled = busy || !servingTokenId;
    if (buttons.skip) buttons.skip.disabled = busy || !servingTokenId;
    if (buttons.complete) buttons.complete.disabled = busy || !servingTokenId;
    if (buttons.recall) buttons.recall.disabled = busy;
    if (btnRecallCustom) btnRecallCustom.disabled = busy;
  }
  async function loadQueue() {
    try {
      refreshEl.textContent = "Updating…";
      const res = await fetch(API_BASE + "/api/v1/queues/" + encodeURIComponent(QUEUE_ID));
      const data = await res.json();
      if (!res.ok) throw new Error((data && data.detail) || "Could not load queue");
      servingEl.textContent = data.serving_token || "—";
      waitingEl.textContent = String(data.waiting_count ?? 0);
      servingTokenId = data.serving_token_id || null;
      setBusy(false);
      refreshEl.textContent = "Updated just now";
    } catch (err) {
      setBusy(false);
      refreshEl.textContent = "Update failed";
      message("Could not load the queue. Check the backend connection.", "error");
    }
  }
  async function action(path, body, success) {
    clearMessage();
    setBusy(true);
    try {
      const res = await fetch(API_BASE + path, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
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
  buttons.call.addEventListener("click", () => action("/api/v1/queues/" + QUEUE_ID + "/call-next", {}, "Next patient called."));
  buttons.hold.addEventListener("click", () => {
    if (servingTokenId) {
      lastActionTokenId = servingTokenId;
      if (recallInput) recallInput.value = lastActionTokenId;
      action("/api/v1/tokens/" + servingTokenId + "/hold", {reason: "Staff hold"}, "Token placed on hold.");
    }
  });
  buttons.skip.addEventListener("click", () => {
    if (servingTokenId) {
      lastActionTokenId = servingTokenId;
      if (recallInput) recallInput.value = lastActionTokenId;
      action("/api/v1/tokens/" + servingTokenId + "/skip", {reason: "No show"}, "Token skipped.");
    }
  });
  buttons.complete.addEventListener("click", () => {
    if (servingTokenId) action("/api/v1/tokens/" + servingTokenId + "/complete", {}, "Visit completed.");
  });

  function handleRecall() {
    const customId = recallInput ? recallInput.value.trim() : "";
    const targetTokenId = customId || servingTokenId || lastActionTokenId;
    if (!targetTokenId) {
      message("Enter a token UUID or hold/skip a token first to recall.", "error");
      return;
    }
    action("/api/v1/tokens/" + targetTokenId + "/recall", {}, "Token recalled to WAITING.");
  }

  buttons.recall.addEventListener("click", handleRecall);
  if (btnRecallCustom) btnRecallCustom.addEventListener("click", handleRecall);

  loadQueue();
  setInterval(loadQueue, CONFIG.STATUS_POLL_INTERVAL_MS);
})();