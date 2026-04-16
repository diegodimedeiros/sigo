(function () {
  function requestCatalog(url, queryParam, queryValue) {
    var fullUrl = new URL(url, window.location.origin);
    fullUrl.searchParams.set(queryParam, queryValue);
    return fetch(fullUrl.toString(), {
      headers: { "X-Requested-With": "XMLHttpRequest" }
    }).then(function (response) {
      if (!response.ok) throw new Error("Falha ao carregar catálogo.");
      return response.json();
    });
  }

  function buildOptions(target, values, placeholder) {
    if (!target) return;
    target.innerHTML = "";
    var firstOption = document.createElement("option");
    firstOption.value = "";
    firstOption.textContent = placeholder || "Selecione";
    target.appendChild(firstOption);
    values.forEach(function (item) {
      var option = document.createElement("option");
      option.value = item.chave;
      option.textContent = item.valor;
      target.appendChild(option);
    });
  }

  function isTruthyValue(value) {
    var normalized = String(value || "").trim().toLowerCase();
    return normalized === "true" || normalized === "1" || normalized === "sim" || normalized === "on";
  }

  function syncToggleFields() {
    document.querySelectorAll(".js-toggle-field").forEach(function (node) {
      var sourceName = node.dataset.toggleSource;
      if (!sourceName) return;
      var source = document.getElementById(sourceName) || document.querySelector('[name="' + sourceName + '"]');
      if (!source) return;
      var active = isTruthyValue(source.value);
      node.style.display = active ? "" : "none";
      node.querySelectorAll("input, select, textarea").forEach(function (field) {
        field.disabled = !active;
      });
    });
  }

  function bindToggle(fieldId) {
    var field = document.getElementById(fieldId);
    if (!field) return;
    field.addEventListener("change", syncToggleFields);
  }

  function syncCatalogSelect(sourceId, targetId, url, queryParam, placeholder) {
    var source = document.getElementById(sourceId);
    var target = document.getElementById(targetId);
    if (!source || !target || !url) return;
    var initialValue = target.dataset.selectedValue || target.value;

    function refresh(resetSelection) {
      var sourceValue = source.value;
      if (!sourceValue) {
        buildOptions(target, [], placeholder);
        return;
      }
      requestCatalog(url, queryParam, sourceValue)
        .then(function (payload) {
          var key = queryParam === "classe" ? "especies" : "locais";
          var values = (((payload || {}).data || {})[key]) || [];
          buildOptions(target, values, "Selecione");
          if (!resetSelection && initialValue) {
            var exists = values.some(function (item) { return item.chave === initialValue; });
            if (exists) {
              target.value = initialValue;
              return;
            }
          }
          target.value = "";
        })
        .catch(function () {
          buildOptions(target, [], placeholder);
        });
    }

    source.addEventListener("change", function () {
      initialValue = "";
      refresh(true);
    });
    refresh(false);
  }

  function triggerFileButtons() {
    document.querySelectorAll("[data-trigger-file]").forEach(function (button) {
      button.addEventListener("click", function () {
        var inputId = button.dataset.triggerFile;
        var input = inputId ? document.getElementById(inputId) : null;
        if (input) input.click();
      });
    });
  }

  function initExistingPhotoRemoval(form) {
    if (!form) return;
    form.querySelectorAll("[data-remove-existing-photo='true']").forEach(function (button) {
      button.addEventListener("click", function () {
        var hiddenName = button.dataset.hiddenName;
        var photoId = button.dataset.photoId;
        var row = button.closest(".js-existing-photo-row");
        if (!hiddenName || !photoId || !row) return;

        var hidden = document.createElement("input");
        hidden.type = "hidden";
        hidden.name = hiddenName;
        hidden.value = photoId;
        form.appendChild(hidden);

        row.remove();
      });
    });
  }

  function renderGeolocation(container, emptyNode, latitude, longitude, hash) {
    window.SesmtGeolocation.render(container, emptyNode, latitude, longitude, hash);
  }

  function renderGeolocationError(container, emptyNode, message) {
    window.SesmtGeolocation.showMessage(container, emptyNode, message);
  }

  function initManejoList() {
    if (!window.SiopAsyncList || typeof window.SiopAsyncList.initAsyncList !== "function") return;
    if (!document.getElementById("manejo-list-form")) return;
    window.SiopAsyncList.initAsyncList({
      formSelector: "#manejo-list-form",
      tableBodySelector: "#manejo-list-body",
      metaSelector: "#manejo-list-meta",
      paginationSelector: "#manejo-list-pagination",
      dataKey: "registros",
      columnCount: 7,
      loadingText: "Carregando manejos...",
      emptyMessage: "Nenhum manejo encontrado.",
      metaText: function (total) {
        return total + " manejo" + (total === 1 ? "" : "s") + " encontrado" + (total === 1 ? "" : "s") + ".";
      },
      renderRow: function (item) {
        return (
          "<tr>" +
          "<td>#"+ window.SiopAsyncList.escapeHtml(item.id) +"</td>" +
          "<td>"+ window.SiopAsyncList.escapeHtml(item.data) +"</td>" +
          "<td>"+ window.SiopAsyncList.escapeHtml(item.classe) +"</td>" +
          "<td>"+ window.SiopAsyncList.escapeHtml(item.nome_popular) +"</td>" +
          "<td>"+ window.SiopAsyncList.escapeHtml(item.area) +"</td>" +
          '<td><span class="badge badge-' + window.SiopAsyncList.escapeHtml(item.status_badge) + '">' + window.SiopAsyncList.escapeHtml(item.status_label) + "</span></td>" +
          '<td class="text-end"><a href="' + window.SiopAsyncList.escapeHtml(item.view_url) + '" class="btn btn-sm btn-label-info">Ver</a></td>' +
          "</tr>"
        );
      }
    });
  }

  function initManejoForm() {
    var form = document.getElementById("manejo-form");
    if (!form) return;

    triggerFileButtons();
    initExistingPhotoRemoval(form);
    bindToggle("realizado_manejo");
    bindToggle("acionado_orgao_publico");
    syncToggleFields();

    var classeField = document.getElementById("classe");
    syncCatalogSelect("classe", "nome_popular", classeField ? classeField.dataset.especiesUrl : "", "classe", "Selecione a classe primeiro");

    var areaCapturaField = document.getElementById("area_captura");
    syncCatalogSelect("area_captura", "local_captura", areaCapturaField ? areaCapturaField.dataset.locaisUrl : "", "area", "Selecione a área primeiro");

    var areaSolturaField = document.getElementById("area_soltura");
    syncCatalogSelect("area_soltura", "local_soltura", areaSolturaField ? areaSolturaField.dataset.locaisUrl : "", "area", "Selecione a área primeiro");

    var capturaGeo = null;
    var solturaGeo = null;

    var realizadoField = document.getElementById("realizado_manejo");
    if (realizadoField) {
      realizadoField.addEventListener("change", function () {
        syncToggleFields();
      });
    }

    window.SesmtPhotoManager.init({
      inputId: "foto_captura",
      statusId: "foto_captura_status",
      listId: "lista_fotos_captura",
      emptyId: "lista_fotos_captura_vazia"
    });

    window.SesmtPhotoManager.init({
      inputId: "foto_soltura",
      statusId: "foto_soltura_status",
      listId: "lista_fotos_soltura",
      emptyId: "lista_fotos_soltura_vazia"
    });

    window.SesmtGeolocation.initCapture({
      latitudeId: "latitude_captura",
      longitudeId: "longitude_captura",
      containerId: "geolocalizacao_captura",
      emptyNodeId: "geolocalizacao_captura_vazia"
    });

    window.SesmtGeolocation.initCapture({
      latitudeId: "latitude_soltura",
      longitudeId: "longitude_soltura",
      containerId: "geolocalizacao_soltura",
      emptyNodeId: "geolocalizacao_soltura_vazia"
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initManejoForm();
    initManejoList();
  });
})();
