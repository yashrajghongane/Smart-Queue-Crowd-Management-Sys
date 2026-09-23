/**
 * frontend-patient/js/register.js
 *
 * Handles the patient registration form:
 *   - Collects name, mobile, department selection
 *   - POSTs to POST /api/v1/registrations/qr
 *   - On success: stores visit_id in sessionStorage, redirects to status.html
 *   - On 409 (duplicate): shows existing token info
 *   - On 422 / network error: shows appropriate error message
 *
 * The backend is the source of truth — no registration logic runs here.
 */

(function () {
  "use strict";

  const API_BASE = window.CONFIG.API_BASE_URL;

  // ── DOM references ──────────────────────────────────────────────────────────
  const form       = document.getElementById("registration-form");
  const nameInput  = document.getElementById("full-name");
  const mobileInput = document.getElementById("mobile");
  const deptSelect = document.getElementById("department");
  const submitBtn  = document.getElementById("submit-btn");
  const statusMsg  = document.getElementById("status-message");
  const loadingEl  = document.getElementById("loading");

  // ── State ───────────────────────────────────────────────────────────────────
  let isSubmitting = false;

  // ── Utilities ───────────────────────────────────────────────────────────────
  function showMessage(text, type) {
    // type: "error" | "info" | "success"
    statusMsg.textContent = text;
    statusMsg.className = "rounded-lg p-4 text-sm mt-4 " + {
      error:   "bg-red-50 text-red-800 border border-red-200",
      info:    "bg-blue-50 text-blue-800 border border-blue-200",
      success: "bg-green-50 text-green-800 border border-green-200",
    }[type];
    statusMsg.classList.remove("hidden");
  }

  function clearMessage() {
    statusMsg.textContent = "";
    statusMsg.classList.add("hidden");
  }

  function setLoading(state) {
    isSubmitting = state;
    if (state) {
      loadingEl.classList.remove("hidden");
      submitBtn.disabled = true;
      submitBtn.textContent = "Registering…";
    } else {
      loadingEl.classList.add("hidden");
      submitBtn.disabled = false;
      submitBtn.textContent = "Get My Token";
    }
  }

  function validateForm() {
    const name   = nameInput.value.trim();
    const mobile = mobileInput.value.trim();
    const dept   = deptSelect.value;

    if (!name) {
      showMessage("Please enter your full name.", "error");
      nameInput.focus();
      return false;
    }
    if (!/^\d{7,15}$/.test(mobile.replace(/\D/g, ""))) {
      showMessage("Please enter a valid mobile number (at least 7 digits).", "error");
      mobileInput.focus();
      return false;
    }
    if (!dept) {
      showMessage("Please select a department.", "error");
      deptSelect.focus();
      return false;
    }
    return true;
  }

  // ── Registration ────────────────────────────────────────────────────────────
  async function submitRegistration(event) {
    event.preventDefault();
    if (isSubmitting) return;
    clearMessage();

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
        // Success — store visit_id and navigate to status page
        sessionStorage.setItem("sq_visit_id",      data.visit_id);
        sessionStorage.setItem("sq_token_number",  data.token_number);
        sessionStorage.setItem("sq_department_id", data.department_id);
        window.location.href = "status.html";
        return;
      }

      if (response.status === 409) {
        // Duplicate active visit — show existing token and link to status
        const detail = data.detail || data;
        sessionStorage.setItem("sq_visit_id",     detail.visit_id);
        sessionStorage.setItem("sq_token_number", detail.token_number);
        showMessage(
          `You already have an active token: ${detail.token_number}. Redirecting to status…`,
          "info"
        );
        setTimeout(() => { window.location.href = "status.html"; }, 2000);
        return;
      }

      if (response.status === 404) {
        showMessage(
          "Department not found. Please ask staff for assistance.",
          "error"
        );
        return;
      }

      if (response.status === 422) {
        // Validation error from the backend
        const errors = data.detail;
        let msg = "Please check your input.";
        if (Array.isArray(errors) && errors.length > 0) {
          msg = errors.map((e) => e.msg).join(" ");
        }
        showMessage(msg, "error");
        return;
      }

      showMessage("Something went wrong. Please try again.", "error");

    } catch (err) {
      console.error("Registration error:", err);
      showMessage(
        "Could not connect to the server. Please check your connection and try again.",
        "error"
      );
    } finally {
      setLoading(false);
    }
  }

  // ── Init ────────────────────────────────────────────────────────────────────
  form.addEventListener("submit", submitRegistration);

  // Clear any stale session data from a previous visit
  sessionStorage.removeItem("sq_visit_id");
  sessionStorage.removeItem("sq_token_number");
  sessionStorage.removeItem("sq_department_id");

})();
