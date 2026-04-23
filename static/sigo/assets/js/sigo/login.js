(function () {
  var REPORTOS_OFFLINE_ACCESS_ENABLED_KEY = "reportos_offline_access_enabled";
  var REPORTOS_OFFLINE_ACCESS_EXPIRES_AT_KEY = "reportos_offline_access_expires_at";

  function getStorageValue(key) {
    try {
      return window.localStorage.getItem(key);
    } catch (_error) {
      return null;
    }
  }

  function hasValidReportosOfflineAccess() {
    var enabled = getStorageValue(REPORTOS_OFFLINE_ACCESS_ENABLED_KEY);
    var expiresAt = Number(getStorageValue(REPORTOS_OFFLINE_ACCESS_EXPIRES_AT_KEY) || 0);

    if (enabled !== "true") {
      return false;
    }

    if (!expiresAt || Number.isNaN(expiresAt)) {
      return false;
    }

    return expiresAt > Date.now();
  }

  function updateReportosOfflineAccessVisibility() {
    var container = document.querySelector("[data-reportos-offline-access]");
    if (!container) {
      return;
    }

    var shouldShow = !navigator.onLine && hasValidReportosOfflineAccess();
    container.hidden = !shouldShow;
    container.classList.toggle("is-visible", shouldShow);
  }

  function initLoginPasswordToggle() {
    var passwordInput = document.getElementById("id_password");
    var toggleButton = document.getElementById("loginPasswordToggle");

    if (!passwordInput || !toggleButton) {
      return;
    }

    toggleButton.addEventListener("click", function () {
      var isHidden = passwordInput.type === "password";
      passwordInput.type = isHidden ? "text" : "password";
      toggleButton.setAttribute("aria-label", isHidden ? "Ocultar senha" : "Mostrar senha");
      toggleButton.setAttribute("aria-pressed", isHidden ? "true" : "false");
      toggleButton.innerHTML = isHidden
        ? '<i class="fas fa-eye-slash" aria-hidden="true"></i>'
        : '<i class="fas fa-eye" aria-hidden="true"></i>';
    });
  }

  function initLoginOfflineAccess() {
    updateReportosOfflineAccessVisibility();
    window.addEventListener("online", updateReportosOfflineAccessVisibility);
    window.addEventListener("offline", updateReportosOfflineAccessVisibility);
    window.addEventListener("storage", updateReportosOfflineAccessVisibility);
  }

  document.addEventListener("DOMContentLoaded", function () {
    initLoginPasswordToggle();
    initLoginOfflineAccess();
  });
}());
