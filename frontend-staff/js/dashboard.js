/**
 * frontend-staff/js/dashboard.js
 *
 * Handles staff dashboard UI logic for viewing queue summary and performing queue actions.
 */

(function() {
  "use strict";

  const API_BASE = window.CONFIG.API_BASE_URL;
  const QUEUE_ID = window.CONFIG.DEFAULT_QUEUE_ID;

  // DOM Elements
  const elServingToken = document.getElementById("serving-token");
  const elWaitingCount = document.getElementById("waiting-count");
  const statusMsg = document.getElementById("status-message");

  const btnCallNext = document.getElementById("btn-call-next");
  const btnHold = document.getElementById("btn-hold");
  const btnRecall = document.getElementById("btn-recall");
  const btnSkip = document.getElementById("btn-skip");
  const btnComplete = document.getElementById("btn-complete");

  let currentServingTokenId = null;

  function showMessage(text, type) {
    statusMsg.textContent = text;
    statusMsg.className = "mb-6 flex items-start gap-3 rounded-xl p-4 border text-base shadow-sm font-medium " + {
      error: "bg-red-50 text-red-700 border-red-200",
      info: "bg-blue-50 text-blue-700 border-blue-200",
      success: "bg-green-50 text-green-700 border-green-200",
    }[type];
    statusMsg.classList.remove("hidden");

    if (type !== 'error') {
      setTimeout(clearMessage, 5000);
    }
  }

  function clearMessage() {
    statusMsg.textContent = "";
    statusMsg.classList.add("hidden");
  }

  async function fetchQueueSummary() {
    try {
      const res = await fetch(`${API_BASE}/api/v1/queues/${QUEUE_ID}`);
      if (!res.ok) throw new Error("Failed to fetch queue summary");
      const data = await res.json();

      elServingToken.textContent = data.serving_token || "--";
      elWaitingCount.textContent = data.waiting_count || "0";
      currentServingTokenId = data.serving_token_id;

    } catch (err) {
      console.error(err);
      showMessage("Connection error when fetching queue summary.", "error");
    }
  }

  async function performAction(urlPath, method, bodyObj = null, successMsg) {
    try {
      const options = {
        method: method,
        headers: { "Content-Type": "application/json" }
      };
      if (bodyObj) {
        options.body = JSON.stringify(bodyObj);
      }

      const res = await fetch(`${API_BASE}${urlPath}`, options);
      const data = await res.json();

      if (!res.ok) {
        const errStr = data.detail && typeof data.detail === 'object' ? data.detail.message || JSON.stringify(data.detail) : data.detail;
        showMessage(`Action failed: ${errStr || 'Unknown error'}`, "error");
        return;
      }

      showMessage(successMsg, "success");
      await fetchQueueSummary();
    } catch (err) {
      console.error(err);
      showMessage("Connection error.", "error");
    }
  }

  btnCallNext.addEventListener("click", () => {
    clearMessage();
    performAction(`/api/v1/queues/${QUEUE_ID}/call-next`, "POST", {}, "Successfully called next patient.");
  });

  btnHold.addEventListener("click", () => {
    clearMessage();
    if (!currentServingTokenId) return showMessage("No token currently serving to hold.", "error");
    performAction(`/api/v1/queues/tokens/${currentServingTokenId}/hold`, "POST", {reason: "Staff hold"}, "Token placed on hold.");
  });

  btnRecall.addEventListener("click", () => {
    clearMessage();
    const tokenId = prompt("Enter the Token ID to recall (In a real app, this would be a list selection):", currentServingTokenId || "");
    if (!tokenId) return;
    performAction(`/api/v1/queues/tokens/${tokenId}/recall`, "POST", {}, "Token recalled.");
  });

  btnSkip.addEventListener("click", () => {
    clearMessage();
    if (!currentServingTokenId) return showMessage("No token currently serving to skip.", "error");
    performAction(`/api/v1/queues/tokens/${currentServingTokenId}/skip`, "POST", {reason: "No show"}, "Token skipped.");
  });

  btnComplete.addEventListener("click", () => {
    clearMessage();
    if (!currentServingTokenId) return showMessage("No token currently serving to complete.", "error");
    performAction(`/api/v1/queues/tokens/${currentServingTokenId}/complete`, "POST", {}, "Visit completed.");
  });

  // Init
  fetchQueueSummary();
  setInterval(fetchQueueSummary, window.CONFIG.STATUS_POLL_INTERVAL_MS || 5000);

})();