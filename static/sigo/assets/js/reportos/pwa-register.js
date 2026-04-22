(function () {
  var REPORTOS_PAGES_CACHE = "reportos-pages";
  var REPORTOS_CATALOGOS_CACHE = "reportos-catalogos";
  var WORKBOX_BACKGROUND_SYNC_DB = "workbox-background-sync";
  var WORKBOX_BACKGROUND_SYNC_STORE = "requests";
  var WORKBOX_BACKGROUND_SYNC_INDEX = "queueName";
  var REPORTOS_SYNC_QUEUE_NAME = "reportos-sesmt-sync";
  var CONNECTIVITY_PROBE_URL = "/reportos/api/catalogos/?_pwa_probe=1";
  var LAST_SYNC_AT_KEY = "reportos_pwa_last_sync_at";
  var LAST_QUEUE_AT_KEY = "reportos_pwa_last_queue_at";
  var LAST_PENDING_COUNT_KEY = "reportos_pwa_last_pending_count";
  var SYNC_STATUS_POLL_MS = 10000;
  var REPORTOS_WARMUP_ROUTES = [
    "/reportos/",
    "/reportos/atendimento/",
    "/reportos/atendimento/lista/",
    "/reportos/atendimento/novo/",
    "/reportos/manejo/",
    "/reportos/manejo/lista/",
    "/reportos/manejo/novo/",
    "/reportos/flora/",
    "/reportos/flora/lista/",
    "/reportos/flora/novo/",
    "/reportos/himenopteros/",
    "/reportos/himenopteros/lista/",
    "/reportos/himenopteros/novo/"
  ];

  function setText(selector, text) {
    var el = document.querySelector(selector);
    if (el) {
      el.textContent = text;
    }
  }

  function setStorageValue(key, value) {
    try {
      window.localStorage.setItem(key, String(value));
    } catch (_error) {
      return;
    }
  }

  function getStorageValue(key) {
    try {
      return window.localStorage.getItem(key);
    } catch (_error) {
      return null;
    }
  }

  function withTimeout(promise, timeoutMs) {
    return new Promise(function (resolve, reject) {
      var timeoutId = setTimeout(function () {
        reject(new Error("timeout"));
      }, timeoutMs);

      promise
        .then(function (result) {
          clearTimeout(timeoutId);
          resolve(result);
        })
        .catch(function (error) {
          clearTimeout(timeoutId);
          reject(error);
        });
    });
  }

  function formatTimestamp(value) {
    if (!value) {
      return "";
    }

    var date = new Date(Number(value));
    if (Number.isNaN(date.getTime())) {
      return "";
    }
    return date.toLocaleString("pt-BR");
  }

  function isHtmlResponse(response) {
    var contentType = (response.headers.get("Content-Type") || "").toLowerCase();
    return contentType.indexOf("text/html") !== -1;
  }

  function warmupReportosPages() {
    if (!navigator.onLine || !("caches" in window) || !("fetch" in window)) {
      return Promise.resolve();
    }

    return caches.open(REPORTOS_PAGES_CACHE).then(function (cache) {
      return Promise.allSettled(
        REPORTOS_WARMUP_ROUTES.map(function (path) {
          return fetch(path, {
            method: "GET",
            credentials: "same-origin",
            headers: {
              "X-Requested-With": "XMLHttpRequest"
            }
          }).then(function (response) {
            if (!response.ok || response.redirected || !isHtmlResponse(response)) {
              return;
            }
            return cache.put(path, response.clone());
          });
        })
      );
    }).catch(function () {
      return Promise.resolve();
    });
  }

  function warmupCatalogos() {
    if (!navigator.onLine || !("caches" in window) || !("fetch" in window)) {
      return Promise.resolve();
    }
    var catalogoPath = "/reportos/api/catalogos/";
    return caches.open(REPORTOS_CATALOGOS_CACHE).then(function (cache) {
      return fetch(catalogoPath, {
        method: "GET",
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest" }
      }).then(function (response) {
        if (!response.ok) return;
        return cache.put(catalogoPath, response.clone());
      });
    }).catch(function () {
      return Promise.resolve();
    });
  }

  function setConnectionDot(isOnline) {
    var dot = document.querySelector("[data-pwa-connection-dot]");
    if (!dot) {
      return;
    }
    dot.classList.remove("text-success", "text-danger", "text-muted");
    dot.classList.add(isOnline ? "text-success" : "text-danger");
  }

  function setServiceWorkerDot(isActive) {
    var dot = document.querySelector("[data-pwa-sw-dot]");
    if (!dot) {
      return;
    }
    dot.classList.remove("text-success", "text-danger", "text-muted");
    dot.classList.add(isActive ? "text-success" : "text-danger");
  }

  function setSyncDot(state) {
    var dot = document.querySelector("[data-pwa-sync-dot]");
    if (!dot) {
      return;
    }
    dot.classList.remove("text-success", "text-danger", "text-muted", "text-warning");
    if (state === "ready") {
      dot.classList.add("text-success");
      return;
    }
    if (state === "pending") {
      dot.classList.add("text-warning");
      return;
    }
    if (state === "error") {
      dot.classList.add("text-danger");
      return;
    }
    dot.classList.add("text-muted");
  }

  function setSyncDetail(text) {
    setText("[data-pwa-sync-detail]", text || "");
  }

  function setDiagnosticText(selector, text) {
    setText(selector, text || "");
  }

  function setDiagnosticList(items) {
    var container = document.querySelector("[data-pwa-diag-cache-list]");
    if (!container) {
      return;
    }
    container.innerHTML = "";

    if (!items || !items.length) {
      var emptyNode = document.createElement("li");
      emptyNode.className = "list-group-item px-0 text-muted";
      emptyNode.textContent = "Nenhum cache ativo encontrado.";
      container.appendChild(emptyNode);
      return;
    }

    items.forEach(function (item) {
      var node = document.createElement("li");
      node.className = "list-group-item px-0";
      node.textContent = item;
      container.appendChild(node);
    });
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

  function listCacheNames() {
    if (!("caches" in window) || typeof caches.keys !== "function") {
      return Promise.resolve(null);
    }
    return caches.keys().catch(function () {
      return null;
    });
  }

  function hasReportosServiceWorker() {
    if (!("serviceWorker" in navigator) || typeof navigator.serviceWorker.getRegistrations !== "function") {
      return Promise.resolve(false);
    }
    return navigator.serviceWorker.getRegistrations().then(function (registrations) {
      return registrations.some(function (registration) {
        return registration && registration.scope && registration.scope.indexOf("/reportos/") !== -1;
      });
    }).catch(function () {
      return false;
    });
  }

  function updateDiagnostics(isOnline, pendingCount) {
    setDiagnosticText("[data-pwa-diag-connection]", isOnline ? "Online" : "Offline");
    setDiagnosticText(
      "[data-pwa-diag-idb]",
      ("indexedDB" in window && typeof indexedDB.open === "function") ? "Disponível" : "Indisponível"
    );
    setDiagnosticText(
      "[data-pwa-diag-cache-api]",
      ("caches" in window && typeof caches.keys === "function") ? "Disponível" : "Indisponível"
    );

    if (pendingCount === null) {
      setDiagnosticText("[data-pwa-diag-pending]", "Leitura indisponível");
    } else {
      setDiagnosticText("[data-pwa-diag-pending]", String(pendingCount));
    }

    var lastSyncAt = formatTimestamp(getStorageValue(LAST_SYNC_AT_KEY));
    var lastQueueAt = formatTimestamp(getStorageValue(LAST_QUEUE_AT_KEY));
    setDiagnosticText("[data-pwa-diag-last-sync]", lastSyncAt || "Sem registro");
    setDiagnosticText("[data-pwa-diag-last-queue]", lastQueueAt || "Sem registro");

    listCacheNames().then(function (cacheNames) {
      if (cacheNames === null) {
        setDiagnosticList(["CacheStorage indisponível neste navegador."]);
        return;
      }
      setDiagnosticList(cacheNames);
    });

    hasReportosServiceWorker().then(function (active) {
      setDiagnosticText("[data-pwa-diag-sw]", active ? "Ativo no escopo /reportos/" : "Não encontrado");
    });
  }

  function updateSyncIndicator(isOnline) {
    return readPendingSyncCount().then(function (pendingCount) {
      var previousCount = Number(getStorageValue(LAST_PENDING_COUNT_KEY) || 0);
      updateDiagnostics(isOnline, pendingCount);

      if (pendingCount === null) {
        setText("[data-pwa-sync-status]", isOnline ? "Monitorando" : "Aguardando conexao");
        setSyncDot("waiting");
        setSyncDetail("Nao foi possivel consultar a fila offline neste navegador.");
        return;
      }

      setStorageValue(LAST_PENDING_COUNT_KEY, pendingCount);

      if (pendingCount > 0) {
        setText("[data-pwa-sync-status]", pendingCount + " pendente" + (pendingCount === 1 ? "" : "s"));
        setSyncDot("pending");
        setSyncDetail(
          isOnline
            ? "Sincronizacao aguardando envio automatico."
            : "Sem conexao. Os registros serao reenviados quando a rede voltar."
        );
        return;
      }

      if (previousCount > 0 && isOnline) {
        setStorageValue(LAST_SYNC_AT_KEY, Date.now());
      }

      if (!isOnline) {
        setText("[data-pwa-sync-status]", "Fila vazia");
        setSyncDot("waiting");
        setSyncDetail("Sem conexao no momento, sem registros pendentes na fila.");
        return;
      }

      setText("[data-pwa-sync-status]", "Fila vazia");
      setSyncDot("ready");

      var lastSyncAt = formatTimestamp(getStorageValue(LAST_SYNC_AT_KEY));
      if (lastSyncAt) {
        setSyncDetail("Ultima sincronizacao concluida em " + lastSyncAt + ".");
        return;
      }

      setSyncDetail("Nenhum registro pendente na fila offline.");
    });
  }

  function probeConnection() {
    if (!("fetch" in window)) {
      return Promise.resolve(Boolean(navigator.onLine));
    }

    if (!navigator.onLine) {
      return Promise.resolve(false);
    }

    return withTimeout(
      fetch(CONNECTIVITY_PROBE_URL, {
        method: "GET",
        credentials: "same-origin",
        cache: "no-store",
        headers: { "X-Requested-With": "XMLHttpRequest" }
      }).then(function (response) {
        return response.ok;
      }).catch(function () {
        return false;
      }),
      2500
    ).catch(function () {
      return false;
    });
  }

  function updateConnectionStatus() {
    return probeConnection().then(function (isOnline) {
      setText("[data-pwa-connection-status]", isOnline ? "Online" : "Offline");
      setConnectionDot(isOnline);
      return updateSyncIndicator(isOnline).then(function () {
        return isOnline;
      });
    });
  }

  updateConnectionStatus();
  window.addEventListener("online", updateConnectionStatus);
  window.addEventListener("offline", updateConnectionStatus);

  if (!("serviceWorker" in navigator)) {
    setText("[data-pwa-sw-status]", "Nao suportado");
    setServiceWorkerDot(false);
    setSyncDot("error");
    setSyncDetail("Service worker indisponivel neste navegador.");
    return;
  }

  navigator.serviceWorker
    .register("/reportos/sw.js", { scope: "/reportos/" })
    .then(function () {
      setText("[data-pwa-sw-status]", "Ativo");
      setServiceWorkerDot(true);
      updateConnectionStatus();
      warmupReportosPages();
      warmupCatalogos();
    })
    .catch(function () {
      setServiceWorkerDot(false);
      setText("[data-pwa-sw-status]", "Indisponivel");
      setText("[data-pwa-sync-status]", "Indisponivel");
      setSyncDot("error");
      setSyncDetail("Nao foi possivel ativar a camada offline do ReportOS.");
    });

  window.addEventListener("online", function () {
    updateConnectionStatus();
    warmupReportosPages();
    warmupCatalogos();
  });

  window.addEventListener("reportos:sync-queued", function () {
    updateConnectionStatus();
  });

  window.addEventListener("reportos:sync-status-refresh", function () {
    updateConnectionStatus();
  });

  window.setInterval(updateConnectionStatus, SYNC_STATUS_POLL_MS);
}());
