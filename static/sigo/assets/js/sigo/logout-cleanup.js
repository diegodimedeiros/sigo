(function () {
  "use strict";

  var REPORTOS_CACHE_PREFIXES = [
    "reportos-",
    "workbox-precache",
  ];
  var REPORTOS_CACHE_NAMES = [
    "reportos-pages",
    "reportos-catalogos",
    "reportos-static",
  ];
  var WORKBOX_BACKGROUND_SYNC_DB = "workbox-background-sync";
  var CLEANUP_TIMEOUT_MS = 1800;

  function withTimeout(promise, timeoutMs) {
    return new Promise(function (resolve) {
      var settled = false;
      var timer = setTimeout(function () {
        if (!settled) {
          settled = true;
          resolve(false);
        }
      }, timeoutMs);

      promise
        .catch(function () {
          return false;
        })
        .then(function () {
          if (settled) {
            return;
          }
          settled = true;
          clearTimeout(timer);
          resolve(true);
        });
    });
  }

  function shouldDeleteCache(cacheName) {
    if (REPORTOS_CACHE_NAMES.indexOf(cacheName) !== -1) {
      return true;
    }
    return REPORTOS_CACHE_PREFIXES.some(function (prefix) {
      return String(cacheName || "").indexOf(prefix) === 0;
    });
  }

  function clearReportosCaches() {
    if (!("caches" in window) || typeof caches.keys !== "function") {
      return Promise.resolve();
    }

    return caches.keys().then(function (cacheNames) {
      return Promise.all(
        cacheNames
          .filter(shouldDeleteCache)
          .map(function (cacheName) {
            return caches.delete(cacheName);
          })
      );
    });
  }

  function unregisterReportosServiceWorkers() {
    if (!("serviceWorker" in navigator) || typeof navigator.serviceWorker.getRegistrations !== "function") {
      return Promise.resolve();
    }

    return navigator.serviceWorker.getRegistrations().then(function (registrations) {
      return Promise.all(
        registrations.map(function (registration) {
          var scope = String(registration.scope || "");
          if (scope.indexOf("/reportos/") === -1) {
            return Promise.resolve(false);
          }
          return registration.unregister();
        })
      );
    });
  }

  function deleteDatabase(name) {
    return new Promise(function (resolve) {
      if (!("indexedDB" in window) || typeof indexedDB.deleteDatabase !== "function") {
        resolve(false);
        return;
      }

      try {
        var request = indexedDB.deleteDatabase(name);
        request.onsuccess = function () {
          resolve(true);
        };
        request.onerror = function () {
          resolve(false);
        };
        request.onblocked = function () {
          resolve(false);
        };
      } catch (_error) {
        resolve(false);
      }
    });
  }

  function clearBackgroundSyncDatabase() {
    return deleteDatabase(WORKBOX_BACKGROUND_SYNC_DB);
  }

  function cleanupReportosOfflineArtifacts() {
    return withTimeout(
      Promise.all([
        clearReportosCaches(),
        unregisterReportosServiceWorkers(),
        clearBackgroundSyncDatabase(),
      ]),
      CLEANUP_TIMEOUT_MS
    );
  }

  function bindLogoutCleanup() {
    document.querySelectorAll('form[data-sigo-logout="true"]').forEach(function (form) {
      if (form.dataset.logoutCleanupBound === "true") {
        return;
      }
      form.dataset.logoutCleanupBound = "true";

      form.addEventListener("submit", function (event) {
        if (form.dataset.logoutCleanupInProgress === "true") {
          return;
        }

        event.preventDefault();
        form.dataset.logoutCleanupInProgress = "true";

        cleanupReportosOfflineArtifacts().finally(function () {
          form.submit();
        });
      });
    });
  }

  if (document.body && document.body.dataset.sigoCleanupOnLoad === "true") {
    cleanupReportosOfflineArtifacts();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindLogoutCleanup);
  } else {
    bindLogoutCleanup();
  }

  window.SigoLogoutCleanup = {
    cleanupReportosOfflineArtifacts: cleanupReportosOfflineArtifacts,
  };
}());
