const API_BASE = '/api/v1';

const els = {
    setupPanel: document.getElementById('setup-panel'),
    queueIdInput: document.getElementById('queue-id-input'),
    btnStart: document.getElementById('btn-start'),
    servingToken: document.getElementById('serving-token'),
    nextToken: document.getElementById('next-token'),
    waitingCount: document.getElementById('waiting-count'),
    lastUpdated: document.getElementById('last-updated'),
    errorMsg: document.getElementById('error-message'),
    errorText: document.getElementById('error-text')
};

let queueId = null;
let pollInterval = null;
let errorTimeout = null;
let lastServing = null;

const showError = (msg) => {
    els.errorText.textContent = msg;
    els.errorMsg.classList.remove('hidden');
    if (errorTimeout) clearTimeout(errorTimeout);
    errorTimeout = setTimeout(() => els.errorMsg.classList.add('hidden'), 10000);
};

const hideError = () => {
    els.errorMsg.classList.add('hidden');
    if (errorTimeout) clearTimeout(errorTimeout);
};

const updateDisplay = (data) => {
    // Flash effect if serving token changes
    const newServing = data.serving_token || '-';
    if (lastServing !== null && lastServing !== '-' && newServing !== lastServing && newServing !== '-') {
        // Play notification sound here if required
        document.body.classList.add('bg-green-900');
        setTimeout(() => document.body.classList.remove('bg-green-900'), 1000);
    }
    lastServing = newServing;

    els.servingToken.textContent = newServing;
    els.nextToken.textContent = data.next_token || '-';
    els.waitingCount.textContent = data.waiting_count || '0';

    const time = new Date().toLocaleTimeString();
    els.lastUpdated.textContent = `Last updated: ${time}`;
};

async function fetchDisplayData() {
    if (!queueId) return;

    try {
        const res = await fetch(`${API_BASE}/public/queues/${queueId}/display`);
        if (!res.ok) {
            const txt = await res.text();
            throw new Error(`HTTP ${res.status}: ${txt}`);
        }
        const data = await res.json();
        hideError();
        updateDisplay(data);
    } catch (err) {
        console.error(err);
        showError(`Connection lost or error: ${err.message}`);
    }
}

const startDisplay = () => {
    const qid = els.queueIdInput.value.trim();
    if (!qid) return;

    queueId = qid;
    els.setupPanel.classList.add('hidden');

    // Initial fetch
    fetchDisplayData();

    // Poll every 5 seconds (fast for display)
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(fetchDisplayData, 5000);
};

// Start via setup panel
els.btnStart.addEventListener('click', startDisplay);

// Or via URL parameter ?queue=...
const urlParams = new URLSearchParams(window.location.search);
const queueParam = urlParams.get('queue');
if (queueParam) {
    els.queueIdInput.value = queueParam;
    startDisplay();
}
