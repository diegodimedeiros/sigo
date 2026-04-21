/* ReportOS Service Worker (Workbox) */
/* global workbox */

importScripts("/static/sigo/assets/vendor/workbox/workbox-sw.js");

if (workbox) {
  workbox.setConfig({
    modulePathPrefix: "/static/sigo/assets/vendor/workbox/",
    debug: false
  });

  /* Precache apenas assets estáticos — nunca páginas Django (são dinâmicas e requerem auth) */
  workbox.precaching.precacheAndRoute([
    { url: "/static/sigo/assets/js/reportos/pwa-register.js", revision: "4" },
    { url: "/static/sigo/assets/js/reportos/catalogos.js", revision: "1" },
    { url: "/static/sigo/assets/js/siop/async-form.js", revision: "4" },
    { url: "/static/sigo/assets/css/sigo-app.css", revision: "2" },
    { url: "/static/sigo/assets/pwa/reportos-offline.html", revision: "1" }
  ]);

  workbox.routing.registerRoute(
    function ({ request, url }) {
      return request.mode === "navigate" && url.pathname.startsWith("/reportos/");
    },
    new workbox.strategies.NetworkFirst({
      cacheName: "reportos-pages",
      networkTimeoutSeconds: 4
    })
  );

  workbox.routing.setCatchHandler(function ({ event }) {
    if (event && event.request && event.request.mode === "navigate") {
      return workbox.precaching.matchPrecache("/static/sigo/assets/pwa/reportos-offline.html");
    }
    return Response.error();
  });

  workbox.routing.registerRoute(
    function ({ url }) {
      return url.pathname.startsWith("/static/");
    },
    new workbox.strategies.StaleWhileRevalidate({
      cacheName: "reportos-static"
    })
  );

  /* Probe de conectividade — nunca servido do cache, deve sempre ir à rede */
  workbox.routing.registerRoute(
    function ({ url }) {
      return url.searchParams.get("_pwa_probe") === "1";
    },
    new workbox.strategies.NetworkOnly()
  );

  workbox.routing.registerRoute(
    function ({ url }) {
      return url.pathname === "/reportos/api/catalogos/";
    },
    new workbox.strategies.StaleWhileRevalidate({
      cacheName: "reportos-catalogos",
      plugins: [
        new workbox.expiration.ExpirationPlugin({ maxAgeSeconds: 60 * 60 * 24 })
      ]
    })
  );

  var bgSyncPlugin = new workbox.backgroundSync.BackgroundSyncPlugin("reportos-sesmt-sync", {
    maxRetentionTime: 24 * 60
  });

  workbox.routing.registerRoute(
    function ({ url, request }) {
      return request.method === "POST" && (
        url.pathname.startsWith("/reportos/api/") ||
        url.pathname.startsWith("/sesmt/api/")
      );
    },
    new workbox.strategies.NetworkOnly({
      plugins: [bgSyncPlugin]
    }),
    "POST"
  );
}

self.addEventListener("install", function () {
  self.skipWaiting();
});

self.addEventListener("message", function (event) {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

self.addEventListener("activate", function (event) {
  event.waitUntil(self.clients.claim());
});
