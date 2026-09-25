/**
 * frontend-patient/js/register.js
 *
 * Handles the patient registration form:
 *   - Collects name, mobile, department selection
 *   - POSTs to POST /api/v1/registrations/qr
 *   - On success (201): stores visit_id in sessionStorage, redirects to status.html
 *   - On 409 (duplicate active visit): shows existing token info, redirects to status.html
 *   - On 422 / network error: shows appropriate inline error
 *
 * The backend is the source of truth — no registration logic runs here.
 */

(function () {
  "use strict";

  const API_BASE = window.CONFIG.API_BASE_URL;

  // ── DOM references ──────────────────────────────────────────────────────────
  const form          = document.getElementById("registration-form");
  const nameInput     = document.getElementById("full-name");
  const mobileInput   = document.getElementById("mobile");
  const deptSelect    = document.getElementById("department");
  const submitBtn     = document.getElementById("submit-btn");
  const submitBtnSpan = submitBtn.querySelector("span");
  const submitSpinner = document.getElementById("submit-spinner");
  const statusMsg     = document.getElementById("status-message");

  const nameError   = document.getElementById("name-error");
  const mobileError = document.getElementById("mobile-error");
  const deptError   = document.getElementById("department-error");

  // ── State ───────────────────────────────────────────────────────────────────
  let isSubmitting = false;

  // ── Utilities ───────────────────────────────────────────────────────────────
  const ICON_ERROR = `<svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`;
  const ICON_INFO  = `<svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`;
  const ICON_OK    = `<svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`;

  const MESSAGE_CLASSES = {
    error:   "bg-red-50 text-red-700 border-red-200",
    info:    "bg-blue-50 text-blue-700 border-blue-200",
    success: "bg-green-50 text-green-700 border-green-200",
  };

  function showMessage(text, type) {
    const icon = type === "info" ? ICON_INFO : type === "success" ? ICON_OK : ICON_ERROR;
    statusMsg.innerHTML = `${icon} <span>${text}</span>`;
    statusMsg.className = `mb-6 flex items-start gap-3 rounded-xl p-4 border text-base shadow-sm font-medium ${MESSAGE_CLASSES[type] || MESSAGE_CLASSES.error}`;
    statusMsg.classList.remove("hidden");
  }

  function clearMessage() {
    statusMsg.innerHTML = "";
    statusMsg.classList.add("hidden");
  }

  function showFieldError(errorEl, inputEl, message) {
    errorEl.querySelector("span").textContent = message;
    errorEl.classList.remove("hidden");
    inputEl.classList.add("border-red-300", "focus:ring-red-500");
    inputEl.classList.remove("border-slate-300", "focus:ring-blue-600");
    inputEl.setAttribute("aria-invalid", "true");
  }

  function clearFieldErrors() {
    [nameError, mobileError, deptError].forEach(el => el.classList.add("hidden"));
    [nameInput, mobileInput, deptSelect].forEach(input => {
      input.classList.remove("border-red-300", "focus:ring-red-500");
      input.classList.add("border-slate-300", "focus:ring-blue-600");
      input.removeAttribute("aria-invalid");
    });
  }

  function setLoading(state) {
    isSubmitting = state;
    if (state) {
      submitBtn.disabled = true;
      submitBtnSpan.textContent = "Processing…";
      submitSpinner.classList.remove("hidden");
      submitSpinner.classList.add("animate-spin");
    } else {
      submitBtn.disabled = false;
      submitBtnSpan.textContent = "Get My Token";
      submitSpinner.classList.add("hidden");
      submitSpinner.classList.remove("animate-spin");
    }
  }

  function validateForm() {
    const name   = nameInput.value.trim();
    const mobile = mobileInput.value.trim();
    const dept   = deptSelect.value;

    let isValid = true;
    clearFieldErrors();
    clearMessage();

    if (!name) {
      showFieldError(nameError, nameInput, "Please enter your full name");
      if (isValid) nameInput.focus();
      isValid = false;
    }
    // Strip non-digit characters before length check (matches backend normalisation)
    if (!/^\d{7,15}$/.test(mobile.replace(/\D/g, ""))) {
      showFieldError(mobileError, mobileInput, "Please enter a valid mobile number (at least 7 digits)");
      if (isValid) mobileInput.focus();
      isValid = false;
    }
    if (!dept) {
      showFieldError(deptError, deptSelect, "Please select a department");
      if (isValid) deptSelect.focus();
      isValid = false;
    }

    if (!isValid) {
      showMessage("Please correct the errors highlighted above.", "error");
    }
    return isValid;
  }

  // ── Registration ────────────────────────────────────────────────────────────
  async function submitRegistration(event) {
    event.preventDefault();
    if (isSubmitting) return;

    if (!validateForm()) return;

    const payload = {
      full_name:     nameInput.value.trim(),
      mobile:        mobileInput.value.trim(),
      department_id: deptSelect.value,
    };

    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/v1/registrations/qr`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(payload),
      });

      const data = await response.json();

      if (response.status === 201) {
        // Success — persist visit data and navigate to status page
        sessionStorage.setItem("sq_visit_id",      data.visit_id);
        sessionStorage.setItem("sq_token_number",  data.token_number);
        sessionStorage.setItem("sq_department_id", data.department_id);
        showMessage(`Token ${data.token_number} registered. Redirecting…`, "success");
        setTimeout(() => { window.location.href = "status.html"; }, 800);
        return;
      }

      if (response.status === 409) {
        // Duplicate active visit — patient already has a token
        const detail = (typeof data.detail === "object") ? data.detail : data;
        sessionStorage.setItem("sq_visit_id",     detail.visit_id);
        sessionStorage.setItem("sq_token_number", detail.token_number);
        // department_id may not be in the 409 payload; preserve existing if set
        if (detail.department_id) {
          sessionStorage.setItem("sq_department_id", detail.department_id);
        }
        showMessage(
          `You already have an active token: ${detail.token_number}. Redirecting to your status…`,
          "info"
        );
        setTimeout(() => { window.location.href = "status.html"; }, 2000);
        return;
      }

      if (response.status === 404) {
        showMessage(
          "Department not found. Please ask a staff member for assistance.",
          "error"
        );
        return;
      }

      if (response.status === 422) {
        // Backend validation error — surface specific field message
        const errors = data.detail;
        let msg = "Please check your input and try again.";
        if (Array.isArray(errors) && errors.length > 0) {
          // Remove Pydantic "Value error, " prefix if present
          msg = errors.map(e => e.msg.replace(/^Value error,\s*/i, "")).join(" ");
        }
        showMessage(msg, "error");
        return;
      }

      // Unexpected status code
      showMessage(`Unexpected response (${response.status}). Please try again.`, "error");

    } catch (err) {
      console.error("Registration error:", err);
      if (!navigator.onLine) {
        showMessage("You appear to be offline. Please check your connection and try again.", "error");
      } else {
        showMessage("Could not connect to the server. Please try again in a moment.", "error");
      }
    } finally {
      setLoading(false);
    }
  }

  // ── Clear stale session data on load ────────────────────────────────────────
  // Only clear if the user explicitly landed on the registration page (not a back-navigation).
  // We always clear to prevent stale session state from a previous registration.
  sessionStorage.removeItem("sq_visit_id");
  sessionStorage.removeItem("sq_token_number");
  sessionStorage.removeItem("sq_department_id");

  // ── Init ────────────────────────────────────────────────────────────────────
  form.addEventListener("submit", submitRegistration);

  // Clear per-field errors when user edits a field after a failed submit
  nameInput.addEventListener("input",   () => { nameError.classList.add("hidden");   nameInput.removeAttribute("aria-invalid"); });
  mobileInput.addEventListener("input", () => { mobileError.classList.add("hidden"); mobileInput.removeAttribute("aria-invalid"); });
  deptSelect.addEventListener("change", () => { deptError.classList.add("hidden");   deptSelect.removeAttribute("aria-invalid"); });

})();
