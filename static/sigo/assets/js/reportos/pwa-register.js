(function () {
  var REPORTOS_PAGES_CACHE = "reportos-pages";
  var REPORTOS_CATALOGOS_CACHE = "reportos-catalogos";
  var CONNECTIVITY_PROBE_URL = "/reportos/api/catalogos/?_pwa_probe=1";
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
    dot.classList.remove("text-success", "text-danger", "text-muted");
    if (state === "ready") {
      dot.classList.add("text-success");
      return;
    }
    if (state === "error") {
      dot.classList.add("text-danger");
      return;
    }
    dot.classList.add("text-muted");
  }

  function updateSyncIndicator(isOnline) {
    if (!isOnline) {
      setText("[data-pwa-sync-status]", "Aguardando conexao");
      setSyncDot("waiting");
      return;
    }

    setText("[data-pwa-sync-status]", "Fila pronta");
    setSyncDot("ready");
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
      updateSyncIndicator(isOnline);
      return isOnline;
    });
  }

  updateConnectionStatus();
  window.addEventListener("online", updateConnectionStatus);
  window.addEventListener("offline", updateConnectionStatus);

  if (!("serviceWorker" in navigator)) {
    setText("[data-pwa-sw-status]", "Nao suportado");
    setServiceWorkerDot(false);
    setSyncDot("error");
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
    });

  window.addEventListener("online", function () {
    updateConnectionStatus();
    warmupReportosPages();
    warmupCatalogos();
  });
})();
