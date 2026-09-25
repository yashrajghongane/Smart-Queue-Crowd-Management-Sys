(function () {
    "use strict";

    const API_BASE = window.location.origin;

    const els = {
        setupPanel: document.getElementById("setup-panel"),
        queueIdInput: document.getElementById("queue-id-input"),
        btnStart: document.getElementById("btn-start"),
        servingToken: document.getElementById("serving-token"),
        nextToken: document.getElementById("next-token"),
        waitingCount: document.getElementById("waiting-count"),
        lastUpdated: document.getElementById("last-updated"),
        errorMsg: document.getElementById("error-message"),
        errorText: document.getElementById("error-text")
    };

    let queueId = null;
    let pollInterval = null;
    let errorTimeout = null;
    let lastServing = null;

    const showError = (msg) => {
        if (!els.errorText || !els.errorMsg) return;
        els.errorText.textContent = msg;
        els.errorMsg.classList.remove("hidden");
        if (errorTimeout) clearTimeout(errorTimeout);
        errorTimeout = setTimeout(() => els.errorMsg.classList.add("hidden"), 10000);
    };

    const hideError = () => {
        if (!els.errorMsg) return;
        els.errorMsg.classList.add("hidden");
        if (errorTimeout) clearTimeout(errorTimeout);
    };

    const updateDisplay = (data) => {
        const newServing = data.serving_token || "-";
        if (lastServing !== null && lastServing !== "-" && newServing !== lastServing && newServing !== "-") {
            document.body.classList.remove("bg-blue-900");
            document.body.classList.add("bg-emerald-900");
            setTimeout(() => {
                document.body.classList.remove("bg-emerald-900");
                document.body.classList.add("bg-blue-900");
            }, 1200);
        }
        lastServing = newServing;

        els.servingToken.textContent = newServing;
        els.nextToken.textContent = data.next_token || "-";
        els.waitingCount.textContent = String(data.waiting_count ?? 0);

        const time = new Date().toLocaleTimeString();
        els.lastUpdated.textContent = `Last updated: ${time}`;
    };

    async function fetchDisplayData() {
        if (!queueId) return;

        try {
            const res = await fetch(`${API_BASE}/api/v1/public/queues/${encodeURIComponent(queueId)}/display`);
            if (!res.ok) {
                const txt = await res.text();
                throw new Error(`HTTP ${res.status}: ${txt}`);
            }
            const data = await res.json();
            hideError();
            updateDisplay(data);
        } catch (err) {
            console.error("Public display error:", err);
            showError(`Display update error: ${err.message}`);
        }
    }

    const startDisplay = () => {
        const qid = els.queueIdInput.value.trim();
        if (!qid) return;

        queueId = qid;
        els.setupPanel.classList.add("hidden");

        fetchDisplayData();

        if (pollInterval) clearInterval(pollInterval);
        pollInterval = setInterval(fetchDisplayData, 5000);
    };

    els.btnStart.addEventListener("click", startDisplay);

    const urlParams = new URLSearchParams(window.location.search);
    const queueParam = urlParams.get("queue");
    if (queueParam) {
        els.queueIdInput.value = queueParam;
        startDisplay();
    } else if (els.queueIdInput.value.trim()) {
        // Auto-start with default queue ID
        startDisplay();
    }
})();
