/* ReportOS — Cache de catálogos para uso offline
 * Carrega /reportos/api/catalogos/ uma vez por sessão e armazena em memória.
 * As funções de formulário consultam window.ReportosCatalogos antes de fazer
 * requisições parametrizadas, permitindo uso offline dos selects dependentes.
 */
(function () {
  "use strict";

  var CATALOGO_URL = "/reportos/api/catalogos/";
  var _data = null;
  var _promise = null;

  function normalizeCatalogKey(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim()
      .toLowerCase();
  }

  function resolveCatalogItems(source, key) {
    if (!source) return null;

    if (Object.prototype.hasOwnProperty.call(source, key)) {
      return Array.isArray(source[key]) ? source[key] : null;
    }

    var normalizedKey = normalizeCatalogKey(key);
    var match = Object.keys(source).find(function (currentKey) {
      return normalizeCatalogKey(currentKey) === normalizedKey;
    });

    if (!match) return null;
    return Array.isArray(source[match]) ? source[match] : null;
  }

  function load() {
    if (_data) return Promise.resolve(_data);
    if (_promise) return _promise;

    var fetchFn = (window.SigoCsrf && typeof window.SigoCsrf.fetch === "function")
      ? window.SigoCsrf.fetch.bind(window.SigoCsrf)
      : window.fetch.bind(window);

    _promise = fetchFn(CATALOGO_URL, {
      headers: { "X-Requested-With": "XMLHttpRequest" }
    })
      .then(function (response) {
        if (!response.ok) throw new Error("Falha ao carregar catálogos.");
        return response.json();
      })
      .then(function (payload) {
        _data = (payload && payload.data) ? payload.data : null;
        _promise = null;
        return _data;
      })
      .catch(function () {
        _promise = null;
        return null;
      });

    return _promise;
  }

  function getLocais(area) {
    if (!_data || !_data.locais_por_area) return null;
    return resolveCatalogItems(_data.locais_por_area, area);
  }

  function getEspecies(classe) {
    if (!_data || !_data.especies_por_classe) return null;
    return resolveCatalogItems(_data.especies_por_classe, classe);
  }

  function getLocaisAsync(area) {
    return load().then(function () {
      return getLocais(area);
    });
  }

  function getEspeciesAsync(classe) {
    return load().then(function () {
      return getEspecies(classe);
    });
  }

  window.ReportosCatalogos = {
    load: load,
    getLocais: getLocais,
    getLocaisAsync: getLocaisAsync,
    getEspecies: getEspecies,
    getEspeciesAsync: getEspeciesAsync,
    get _ready() { return _data !== null; }
  };

  /* Pré-carrega assim que o script é executado */
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", load);
  } else {
    load();
  }
}());
