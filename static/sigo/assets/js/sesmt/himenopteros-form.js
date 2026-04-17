(function () {
  function requestCatalog(url, queryParam, queryValue) {
    var fullUrl = new URL(url, window.location.origin);
    fullUrl.searchParams.set(queryParam, queryValue);
    return window.SigoCsrf.fetch(fullUrl.toString(), {
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

  function triggerFileButtons() {
    document.querySelectorAll("[data-trigger-file]").forEach(function (button) {
      button.addEventListener("click", function () {
        var input = document.getElementById(button.dataset.triggerFile || "");
        if (input) input.click();
      });
    });
  }

  function syncAreaLocais() {
    var area = document.getElementById("himenopteros-area");
    var local = document.getElementById("himenopteros-local");
    if (!area || !local) return;
    var initialValue = local.dataset.selectedValue || local.value;
    function refresh(resetSelection) {
      var areaValue = area.value;
      if (!areaValue) {
        buildOptions(local, [], "Selecione");
        return;
      }
      requestCatalog(area.dataset.locaisUrl, "area", areaValue)
        .then(function (payload) {
          var values = (((payload || {}).data || {}).locais) || [];
          buildOptions(local, values, "Selecione");
          if (!resetSelection && initialValue) {
            var exists = values.some(function (item) { return item.chave === initialValue; });
            if (exists) {
              local.value = initialValue;
              return;
            }
          }
          local.value = "";
        })
        .catch(function () { buildOptions(local, [], "Selecione"); });
    }
    area.addEventListener("change", function () {
      initialValue = "";
      refresh(true);
    });
    refresh(false);
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

  function renderGeolocation(container, emptyNode, latitude, longitude) {
    window.SesmtGeolocation.render(container, emptyNode, latitude, longitude);
  }

  function renderGeolocationError(container, emptyNode, message) {
    window.SesmtGeolocation.showMessage(container, emptyNode, message);
  }

  function initHimenopterosList() {
    if (!window.SiopAsyncList || typeof window.SiopAsyncList.initAsyncList !== "function") return;
    if (!document.getElementById("himenopteros-list-form")) return;
    window.SiopAsyncList.initAsyncList({
      formSelector: "#himenopteros-list-form",
      tableBodySelector: "#himenopteros-list-body",
      metaSelector: "#himenopteros-list-meta",
      paginationSelector: "#himenopteros-list-pagination",
      dataKey: "registros",
      columnCount: 7,
      loadingText: "Carregando registros de himenópteros...",
      emptyMessage: "Nenhum registro encontrado.",
      metaText: function (total) {
        return total + " registro" + (total === 1 ? "" : "s") + " encontrado" + (total === 1 ? "" : "s") + ".";
      },
      renderRow: function (item) {
        return (
          "<tr>" +
          "<td>#"+ window.SiopAsyncList.escapeHtml(item.id) +"</td>" +
          "<td>"+ window.SiopAsyncList.escapeHtml(item.data) +"</td>" +
          "<td>"+ window.SiopAsyncList.escapeHtml(item.tipo_himenoptero) +"</td>" +
          "<td>"+ window.SiopAsyncList.escapeHtml(item.area) +"</td>" +
          "<td>"+ window.SiopAsyncList.escapeHtml(item.risco) +"</td>" +
          '<td><span class="badge badge-' + window.SiopAsyncList.escapeHtml(item.status_badge) + '">' + window.SiopAsyncList.escapeHtml(item.status_label) + "</span></td>" +
          '<td class="text-end"><a href="' + window.SiopAsyncList.escapeHtml(item.view_url) + '" class="btn btn-sm btn-label-info">Ver</a></td>' +
          "</tr>"
        );
      }
    });
  }

  function initHimenopterosForm() {
    var form = document.getElementById("himenopteros-form");
    if (!form) return;
    triggerFileButtons();
    syncAreaLocais();
    initExistingPhotoRemoval(form);

    window.SesmtPhotoManager.init({
      inputId: "himenopteros_fotos",
      statusId: "himenopteros_fotos_status",
      listId: "lista_himenopteros_fotos",
      emptyId: "lista_himenopteros_fotos_vazia"
    });

    window.SesmtGeolocation.initCapture({
      latitudeId: "himenopteros-latitude",
      longitudeId: "himenopteros-longitude",
      containerId: "geolocalizacao_himenopteros",
      emptyNodeId: "geolocalizacao_himenopteros_vazia"
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initHimenopterosForm();
    initHimenopterosList();
  });
})();
