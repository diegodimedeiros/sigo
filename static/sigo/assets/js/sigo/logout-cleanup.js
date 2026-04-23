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
  var WORKBOX_BACKGROUND_SYNC_STORE = "requests";
  var WORKBOX_BACKGROUND_SYNC_INDEX = "queueName";
  var REPORTOS_SYNC_QUEUE_NAME = "reportos-sesmt-sync";
  var CLEANUP_TIMEOUT_MS = 1800;
  var LOGIN_PATH = "/login/";
  var REPORTOS_OFFLINE_STORAGE_KEYS = [
    "reportos_offline_access_enabled",
    "reportos_offline_access_authorized_at",
    "reportos_offline_access_expires_at",
    "reportos_pwa_last_sync_at",
    "reportos_pwa_last_queue_at",
    "reportos_pwa_last_pending_count",
  ];

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

  function readPendingSyncCount() {
    return new Promise(function (resolve) {
      if (!("indexedDB" in window) || typeof indexedDB.open !== "function") {
        resolve(null);
        return;
      }

      var request;
      try {
        request = indexedDB.open(WORKBOX_BACKGROUND_SYNC_DB);
      } catch (_error) {
        resolve(null);
        return;
      }

      request.onerror = function () {
        resolve(null);
      };
      request.onblocked = function () {
        resolve(null);
      };
      request.onsuccess = function () {
        var database = request.result;
        if (!database.objectStoreNames.contains(WORKBOX_BACKGROUND_SYNC_STORE)) {
          database.close();
          resolve(0);
          return;
        }

        try {
          var transaction = database.transaction(WORKBOX_BACKGROUND_SYNC_STORE, "readonly");
          var store = transaction.objectStore(WORKBOX_BACKGROUND_SYNC_STORE);
          if (!store.indexNames.contains(WORKBOX_BACKGROUND_SYNC_INDEX)) {
            database.close();
            resolve(null);
            return;
          }
          var index = store.index(WORKBOX_BACKGROUND_SYNC_INDEX);
          var countRequest = index.count(REPORTOS_SYNC_QUEUE_NAME);
          countRequest.onerror = function () {
            database.close();
            resolve(null);
          };
          countRequest.onsuccess = function () {
            database.close();
            resolve(Number(countRequest.result || 0));
          };
        } catch (_error) {
          database.close();
          resolve(null);
        }
      };
    });
  }

  function getFallbackPendingSyncCount() {
    try {
      return Number(window.localStorage.getItem("reportos_pwa_last_pending_count") || 0);
    } catch (_error) {
      return 0;
    }
  }

  function ensurePendingSyncModalStyles() {
    if (document.getElementById("sigoPendingSyncModalStyles")) {
      return;
    }

    var styleTag = document.createElement("style");
    styleTag.id = "sigoPendingSyncModalStyles";
    styleTag.textContent = [
      ".sigo-pending-sync-modal{position:fixed;inset:0;z-index:1080;display:flex;align-items:center;justify-content:center;padding:1rem;background:rgba(15,23,42,0.48);backdrop-filter:blur(4px);}",
      ".sigo-pending-sync-modal__dialog{width:min(100%,30rem);background:rgba(255,255,255,0.98);border:1px solid rgba(255,255,255,0.55);border-radius:1.5rem;box-shadow:0 24px 70px rgba(15,23,42,0.22);padding:1.35rem;}",
      ".sigo-pending-sync-modal__eyebrow{display:inline-flex;align-items:center;gap:.4rem;margin-bottom:.75rem;padding:.35rem .7rem;border-radius:999px;background:rgba(21,114,232,0.1);color:#1572e8;font-size:.78rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase;}",
      ".sigo-pending-sync-modal__title{margin:0 0 .55rem;color:#243247;font-size:1.35rem;font-weight:800;line-height:1.25;}",
      ".sigo-pending-sync-modal__copy{margin:0;color:#64748b;font-size:.95rem;line-height:1.6;}",
      ".sigo-pending-sync-modal__actions{display:flex;justify-content:flex-end;gap:.75rem;margin-top:1.25rem;}",
      ".sigo-pending-sync-modal__button{min-height:2.85rem;padding:0 1rem;border-radius:.95rem;border:1px solid transparent;font-weight:700;cursor:pointer;}",
      ".sigo-pending-sync-modal__button--ghost{background:#ffffff;border-color:rgba(100,116,139,0.22);color:#475569;}",
      ".sigo-pending-sync-modal__button--danger{background:linear-gradient(135deg,#1572e8,#48abf7);color:#ffffff;box-shadow:0 16px 32px rgba(21,114,232,0.2);}",
      "@media (max-width: 640px){.sigo-pending-sync-modal__dialog{padding:1.1rem;}.sigo-pending-sync-modal__actions{flex-direction:column;}.sigo-pending-sync-modal__button{width:100%;}}"
    ].join("");
    document.head.appendChild(styleTag);
  }

  function confirmPendingSyncDiscard(pendingCount) {
    if (!pendingCount || pendingCount < 1) {
      return Promise.resolve(true);
    }

    ensurePendingSyncModalStyles();

    return new Promise(function (resolve) {
      var modal = document.createElement("div");
      modal.className = "sigo-pending-sync-modal";
      modal.innerHTML = [
        '<div class="sigo-pending-sync-modal__dialog" role="dialog" aria-modal="true" aria-labelledby="sigoPendingSyncModalTitle">',
        '  <div class="sigo-pending-sync-modal__eyebrow"><i class="fas fa-wifi" aria-hidden="true"></i> Logout offline</div>',
        '  <h2 class="sigo-pending-sync-modal__title" id="sigoPendingSyncModalTitle">Existem ' + pendingCount + " registro" + (pendingCount === 1 ? "" : "s") + ' pendente' + (pendingCount === 1 ? "" : "s") + "</h2>",
        '  <p class="sigo-pending-sync-modal__copy">Ainda existem dados do ReportOS aguardando sincronizacao. Se voce sair agora, esses registros locais serao descartados e nao poderao ser enviados depois.</p>',
        '  <div class="sigo-pending-sync-modal__actions">',
        '    <button type="button" class="sigo-pending-sync-modal__button sigo-pending-sync-modal__button--ghost" data-pending-sync-cancel>Continuar conectado</button>',
        '    <button type="button" class="sigo-pending-sync-modal__button sigo-pending-sync-modal__button--danger" data-pending-sync-confirm>Sair e descartar</button>',
        "  </div>",
        "</div>"
      ].join("");

      function finalize(confirmed) {
        document.removeEventListener("keydown", handleKeydown);
        modal.remove();
        resolve(confirmed);
      }

      function handleKeydown(event) {
        if (event.key === "Escape") {
          finalize(false);
        }
      }

      modal.addEventListener("click", function (event) {
        if (event.target === modal) {
          finalize(false);
        }
      });

      modal.querySelector("[data-pending-sync-cancel]").addEventListener("click", function () {
        finalize(false);
      });

      modal.querySelector("[data-pending-sync-confirm]").addEventListener("click", function () {
        finalize(true);
      });

      document.addEventListener("keydown", handleKeydown);
      document.body.appendChild(modal);
      modal.querySelector("[data-pending-sync-cancel]").focus();
    });
  }

  function clearReportosOfflineStorage() {
    try {
      REPORTOS_OFFLINE_STORAGE_KEYS.forEach(function (key) {
        window.localStorage.removeItem(key);
      });
    } catch (_error) {
      return false;
    }
    return true;
  }

  function cleanupReportosOfflineArtifacts() {
    return withTimeout(
      Promise.all([
        clearReportosCaches(),
        unregisterReportosServiceWorkers(),
        clearBackgroundSyncDatabase(),
        Promise.resolve(clearReportosOfflineStorage()),
      ]),
      CLEANUP_TIMEOUT_MS
    );
  }

  function getLogoutRequestConfig(form) {
    var csrfInput = form.querySelector('input[name="csrfmiddlewaretoken"]');
    return {
      url: form.getAttribute("action") || "/logout/",
      csrfToken: csrfInput ? csrfInput.value : "",
    };
  }

  function performServerLogout(config) {
    if (!config || !config.url || !("fetch" in window)) {
      return Promise.resolve(false);
    }

    return fetch(config.url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": config.csrfToken || "",
      },
      body: "csrfmiddlewaretoken=" + encodeURIComponent(config.csrfToken || ""),
    }).then(function (response) {
      return response.ok || response.redirected;
    }).catch(function () {
      return false;
    });
  }

  function redirectToLogin() {
    window.location.replace(LOGIN_PATH);
  }

  function showOfflineLogoutFallback(logoutRequestConfig) {
    var pageTitle = "Logout concluido";
    var markup = [
      '<main class="sigo-offline-login" role="main">',
      '  <section class="sigo-offline-login__brand" aria-label="Identidade do sistema">',
      '    <div class="sigo-offline-login__brand-row">',
      '      <img class="sigo-offline-login__logo" src="/static/sigo/assets/img/sigo/logo_light.svg" alt="SIGO" />',
      '      <div>',
      '        <h1 class="sigo-offline-login__brand-title">SIGO</h1>',
      '        <p class="sigo-offline-login__brand-copy">Sistema Integrado de Gestao Operacional</p>',
      '      </div>',
      '    </div>',
      '  </section>',
      '  <section class="sigo-offline-login__card" aria-label="Login offline">',
      '    <div class="sigo-offline-login__header">',
      '      <h2 class="sigo-offline-login__title">Login</h2>',
      '      <p class="sigo-offline-login__subtitle">Sua sessao local foi encerrada com seguranca.</p>',
      '    </div>',
      '    <div class="sigo-offline-login__alert" data-offline-logout-alert>',
      '      <strong>Sem conexao.</strong> O acesso offline do ReportOS foi removido deste dispositivo. Para entrar novamente com usuario e senha, conecte-se a internet.',
      '    </div>',
      '    <form class="sigo-offline-login__form" novalidate>',
      '      <label class="sigo-offline-login__label" for="offline-username">Usuario</label>',
      '      <input id="offline-username" class="sigo-offline-login__input" type="text" placeholder="Seu usuario" disabled />',
      '      <label class="sigo-offline-login__label" for="offline-password">Senha</label>',
      '      <input id="offline-password" class="sigo-offline-login__input" type="password" placeholder="Sua senha" disabled />',
      '      <button class="sigo-offline-login__button" type="button" disabled>Conecte-se para entrar</button>',
      '    </form>',
      '    <p class="sigo-offline-login__helper">Quando a internet voltar, acesse o login normalmente para iniciar uma nova sessao.</p>',
      '  </section>',
      '</main>'
    ].join("");
    var styles = [
      "body{margin:0;min-height:100vh;padding:1rem;background:linear-gradient(135deg,rgba(21,114,232,.66),rgba(72,171,247,.34)),url('/static/sigo/assets/img/institucional/login_wall.png') center center / cover no-repeat;font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#1f2937;display:flex;align-items:center;justify-content:center;}",
      ".sigo-offline-login{width:min(100%,34rem);display:grid;gap:1rem;}",
      ".sigo-offline-login__brand,.sigo-offline-login__card{background:rgba(255,255,255,0.94);border:1px solid rgba(255,255,255,0.55);border-radius:1.6rem;box-shadow:0 24px 70px rgba(15,23,42,0.22);}",
      ".sigo-offline-login__brand{padding:1.1rem 1.25rem;}",
      ".sigo-offline-login__brand-row{display:flex;align-items:center;gap:.9rem;}",
      ".sigo-offline-login__logo{width:4rem;height:4rem;padding:.55rem;border-radius:1.15rem;background:linear-gradient(135deg,#1572e8,#48abf7);box-shadow:0 16px 32px rgba(21,114,232,0.24);box-sizing:border-box;}",
      ".sigo-offline-login__brand-title{margin:0;color:#243247;font-size:2rem;font-weight:800;line-height:1;}",
      ".sigo-offline-login__brand-copy{margin:.3rem 0 0;color:#64748b;font-size:.95rem;}",
      ".sigo-offline-login__card{padding:1.6rem;}",
      ".sigo-offline-login__header{text-align:center;margin-bottom:1.25rem;}",
      ".sigo-offline-login__title{margin:0 0 .45rem;color:#243247;font-size:2rem;font-weight:800;}",
      ".sigo-offline-login__subtitle{margin:0;color:#64748b;font-size:.98rem;line-height:1.5;}",
      ".sigo-offline-login__alert{margin-bottom:1.2rem;padding:.95rem 1rem;border-radius:1rem;background:rgba(21,114,232,0.08);border:1px solid rgba(21,114,232,0.16);color:#40536b;font-size:.92rem;line-height:1.55;}",
      ".sigo-offline-login__form{display:grid;gap:.8rem;}",
      ".sigo-offline-login__label{color:#4b5563;font-size:.8rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;}",
      ".sigo-offline-login__input{min-height:3.45rem;padding:0 1rem;border-radius:1rem;border:1px solid rgba(84,79,104,0.14);background:rgba(226,236,251,0.62);color:#475569;box-sizing:border-box;}",
      ".sigo-offline-login__input::placeholder{color:#94a3b8;}",
      ".sigo-offline-login__button{margin-top:.35rem;min-height:3.4rem;border:0;border-radius:1rem;background:linear-gradient(135deg,#9eb6d2,#bdd3ea);color:#fff;font-weight:700;cursor:not-allowed;opacity:1;}",
      ".sigo-offline-login__helper{margin:1rem 0 0;text-align:center;color:#64748b;font-size:.9rem;line-height:1.55;}",
      "@media (max-width: 640px){body{padding:.85rem;}.sigo-offline-login__brand,.sigo-offline-login__card{border-radius:1.4rem;}.sigo-offline-login__card{padding:1.25rem;}.sigo-offline-login__brand-title{font-size:1.85rem;}.sigo-offline-login__title{font-size:1.75rem;}}"
    ].join("");

    try {
      window.history.replaceState({}, "", LOGIN_PATH);
    } catch (_error) {
      // Mantem a tela local mesmo se o navegador impedir a troca da URL.
    }

    document.title = pageTitle;
    document.body.innerHTML = markup;

    var styleTag = document.createElement("style");
    styleTag.textContent = styles;
    document.head.appendChild(styleTag);

    window.addEventListener("online", function () {
      var alertNode = document.querySelector("[data-offline-logout-alert]");
      if (alertNode) {
        alertNode.innerHTML = "<strong>Conexao restabelecida.</strong> Finalizando o logout com o servidor e abrindo o login...";
      }

      performServerLogout(logoutRequestConfig).finally(function () {
        redirectToLogin();
      });
    }, { once: true });
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
        readPendingSyncCount().then(function (pendingCount) {
          var effectivePendingCount = pendingCount;
          if (effectivePendingCount === null) {
            effectivePendingCount = getFallbackPendingSyncCount();
          }

          confirmPendingSyncDiscard(effectivePendingCount).then(function (shouldProceed) {
            if (!shouldProceed) {
              form.dataset.logoutCleanupInProgress = "false";
              return;
            }

            form.dataset.logoutCleanupInProgress = "true";
            var logoutRequestConfig = getLogoutRequestConfig(form);

            cleanupReportosOfflineArtifacts().finally(function () {
              if (!navigator.onLine) {
                showOfflineLogoutFallback(logoutRequestConfig);
                return;
              }
              form.submit();
            });
          });
        }).catch(function () {
          form.dataset.logoutCleanupInProgress = "true";
          var logoutRequestConfig = getLogoutRequestConfig(form);

          cleanupReportosOfflineArtifacts().finally(function () {
            if (!navigator.onLine) {
              showOfflineLogoutFallback(logoutRequestConfig);
              return;
            }
            form.submit();
          });
        });
      });
    });
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
