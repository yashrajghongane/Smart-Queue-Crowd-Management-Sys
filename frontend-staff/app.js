const API_BASE = '/api/v1';

// DOM Elements
const els = {
    queueId: document.getElementById('queue-id-input'),
    zoneId: document.getElementById('zone-id-input'),
    btnRefresh: document.getElementById('btn-refresh'),
    btnRefreshZone: document.getElementById('btn-refresh-zone'),
    btnCallNext: document.getElementById('btn-call-next'),
    btnComplete: document.getElementById('btn-complete'),
    btnSkip: document.getElementById('btn-skip'),
    btnHold: document.getElementById('btn-hold'),
    btnRecall: document.getElementById('btn-recall'),
    recallTokenId: document.getElementById('recall-token-id'),
    servingToken: document.getElementById('serving-token'),
    waitingCount: document.getElementById('waiting-count'),
    zoneOccupancy: document.getElementById('zone-occupancy'),
    zoneCapacity: document.getElementById('zone-capacity'),
    capacityAlert: document.getElementById('capacity-alert'),
    errorMsg: document.getElementById('error-message'),
    errorText: document.getElementById('error-text'),
    lastUpdated: document.getElementById('last-updated')
};

let currentServingTokenId = null;

// Utility functions
const showError = (msg) => {
    els.errorText.textContent = msg;
    els.errorMsg.classList.remove('hidden');
    setTimeout(() => els.errorMsg.classList.add('hidden'), 5000);
};

const updateTimestamp = () => {
    els.lastUpdated.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
};

const setLoading = (btn, isLoading) => {
    if (isLoading) {
        btn.dataset.originalText = btn.textContent;
        btn.textContent = '...';
        btn.disabled = true;
    } else {
        btn.textContent = btn.dataset.originalText || btn.textContent;
        btn.disabled = false;
    }
};

const updateActionButtons = (hasServing) => {
    els.btnComplete.disabled = !hasServing;
    els.btnSkip.disabled = !hasServing;
    els.btnHold.disabled = !hasServing;
};

// API Calls
async function fetchQueueSummary() {
    const qid = els.queueId.value.trim();
    if (!qid) return;

    try {
        const res = await fetch(`${API_BASE}/queues/${qid}`);
        if (!res.ok) {
            const txt = await res.text();
            throw new Error(`HTTP ${res.status}: ${txt}`);
        }
        const data = await res.json();

        els.servingToken.textContent = data.serving_token || '-';
        els.waitingCount.textContent = data.waiting_count || '0';
        currentServingTokenId = data.serving_token_id;

        updateActionButtons(!!currentServingTokenId);
        updateTimestamp();
    } catch (err) {
        console.error(err);
        showError(`Failed to load queue summary: ${err.message}`);
    }
}

async function fetchZoneOccupancy() {
    const zid = els.zoneId.value.trim();
    if (!zid) return;

    try {
        const res = await fetch(`${API_BASE}/zones/${zid}/occupancy`);
        if (!res.ok) {
             if (res.status === 404 || res.status === 501) {
                 console.warn(`Zone occupancy endpoint not available (${res.status})`);
                 return; // Silently ignore if zone endpoint isn't fully built yet
             }
             const txt = await res.text();
             throw new Error(`HTTP ${res.status}: ${txt}`);
        }
        const data = await res.json();

        els.zoneOccupancy.textContent = data.occupancy;
        els.zoneCapacity.textContent = `/ ${data.capacity}`;

        els.capacityAlert.textContent = data.capacity_alert;
        els.capacityAlert.className = 'mt-4 px-4 py-1 rounded-full font-bold text-sm';

        switch (data.capacity_alert) {
            case 'NORMAL': els.capacityAlert.classList.add('bg-green-200', 'text-green-800'); break;
            case 'MODERATE': els.capacityAlert.classList.add('bg-yellow-200', 'text-yellow-800'); break;
            case 'HIGH': els.capacityAlert.classList.add('bg-orange-200', 'text-orange-800'); break;
            case 'CRITICAL': els.capacityAlert.classList.add('bg-red-200', 'text-red-800'); break;
            default: els.capacityAlert.classList.add('bg-gray-200', 'text-gray-800');
        }

    } catch (err) {
        console.error(err);
        // Don't show global error for zone yet since it might not be implemented
        // showError(`Failed to load zone occupancy: ${err.message}`);
    }
}

async function performQueueAction(action, tokenId = null, body = null) {
    const qid = els.queueId.value.trim();
    let url = `${API_BASE}/queues/${qid}/${action}`;

    if (tokenId) {
        url = `${API_BASE}/tokens/${tokenId}/${action}`;
    }

    try {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: body ? JSON.stringify(body) : JSON.stringify({})
        });

        if (!res.ok) {
            let errMsg = `HTTP ${res.status}`;
            try {
                const errData = await res.json();
                errMsg = errData.detail || errData.message || errMsg;
            } catch (e) {
                errMsg = await res.text();
            }
            throw new Error(errMsg);
        }

        await fetchQueueSummary();
    } catch (err) {
        console.error(err);
        showError(`Action failed: ${err.message}`);
    }
}

// Event Listeners
els.btnRefresh.addEventListener('click', () => {
    fetchQueueSummary();
    fetchZoneOccupancy();
});

els.btnRefreshZone.addEventListener('click', fetchZoneOccupancy);

els.btnCallNext.addEventListener('click', async (e) => {
    setLoading(e.target, true);
    await performQueueAction('call-next');
    setLoading(e.target, false);
});

els.btnComplete.addEventListener('click', async (e) => {
    if (!currentServingTokenId) return;
    setLoading(e.target, true);
    await performQueueAction('complete', currentServingTokenId);
    setLoading(e.target, false);
});

els.btnSkip.addEventListener('click', async (e) => {
    if (!currentServingTokenId) return;
    const reason = prompt("Reason for skipping (optional):");
    setLoading(e.target, true);
    await performQueueAction('skip', currentServingTokenId, { reason });
    setLoading(e.target, false);
});

els.btnHold.addEventListener('click', async (e) => {
    if (!currentServingTokenId) return;
    const reason = prompt("Reason for holding (optional):");
    setLoading(e.target, true);
    await performQueueAction('hold', currentServingTokenId, { reason });
    setLoading(e.target, false);
});

els.btnRecall.addEventListener('click', async (e) => {
    const tid = els.recallTokenId.value.trim();
    if (!tid) {
        showError("Please enter a Token ID to recall");
        return;
    }
    setLoading(e.target, true);
    await performQueueAction('recall', tid);
    setLoading(e.target, false);
    els.recallTokenId.value = '';
});

// Initial load
fetchQueueSummary();
fetchZoneOccupancy();

// Auto refresh every 10 seconds
setInterval(() => {
    fetchQueueSummary();
    fetchZoneOccupancy();
}, 10000);
