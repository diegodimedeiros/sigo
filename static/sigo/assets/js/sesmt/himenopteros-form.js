(function () {
  function requestCatalog(url, queryParam, queryValue) {
    if (window.ReportosCatalogos && queryParam === "area") {
      return window.ReportosCatalogos.getLocaisAsync(queryValue).then(function (cached) {
        if (cached !== null) {
          return { ok: true, data: { locais: cached } };
        }

        var fullUrl = new URL(url, window.location.origin);
        fullUrl.searchParams.set(queryParam, queryValue);
        var fetchFn = (window.SigoCsrf && typeof window.SigoCsrf.fetch === "function")
          ? window.SigoCsrf.fetch.bind(window.SigoCsrf)
          : window.fetch.bind(window);
        return fetchFn(fullUrl.toString(), {
          headers: { "X-Requested-With": "XMLHttpRequest" }
        }).then(function (response) {
          if (!response.ok) throw new Error("Falha ao carregar catálogo.");
          return response.json();
        });
      });
    }

    var fullUrl = new URL(url, window.location.origin);
    fullUrl.searchParams.set(queryParam, queryValue);
    var fetchFn = (window.SigoCsrf && typeof window.SigoCsrf.fetch === "function")
      ? window.SigoCsrf.fetch.bind(window.SigoCsrf)
      : window.fetch.bind(window);
    return fetchFn(fullUrl.toString(), {
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
      var catalogPromise;
      try {
        catalogPromise = requestCatalog(area.dataset.locaisUrl, "area", areaValue);
      } catch (_err) {
        buildOptions(local, [], "Selecione");
        return;
      }
      catalogPromise
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

    if (window.SesmtPhotoManager && typeof window.SesmtPhotoManager.init === "function") {
      window.SesmtPhotoManager.init({
        inputId: "himenopteros_fotos",
        statusId: "himenopteros_fotos_status",
        listId: "lista_himenopteros_fotos",
        emptyId: "lista_himenopteros_fotos_vazia"
      });
    }

    if (window.SesmtGeolocation && typeof window.SesmtGeolocation.initCapture === "function") {
      window.SesmtGeolocation.initCapture({
        latitudeId: "himenopteros-latitude",
        longitudeId: "himenopteros-longitude",
        containerId: "geolocalizacao_himenopteros",
        emptyNodeId: "geolocalizacao_himenopteros_vazia"
      });
    }

      // Validação required frontend
      form.addEventListener("submit", function (event) {
        var errors = [];
        var firstInvalid = null;
        function markInvalid(id, msg) {
          var el = document.getElementById(id);
          if (!el) return;
          el.classList.add("is-invalid");
          var msgNode = document.createElement("div");
          msgNode.className = "invalid-feedback";
          msgNode.textContent = msg;
          if (el.nextSibling) el.parentNode.insertBefore(msgNode, el.nextSibling);
          else el.parentNode.appendChild(msgNode);
          if (!firstInvalid) firstInvalid = el;
        }
        function val(id) {
          var el = document.getElementById(id);
          return el && el.value ? el.value.trim() : "";
        }
        // Limpa marcações antigas
        form.querySelectorAll(".is-invalid").forEach(function (el) { el.classList.remove("is-invalid"); });
        form.querySelectorAll(".invalid-feedback").forEach(function (el) { el.remove(); });
        // Latitude e longitude obrigatórios
        if (!val("himenopteros-latitude")) { errors.push("Informe a latitude."); markInvalid("himenopteros-latitude", "Campo obrigatório"); }
        if (!val("himenopteros-longitude")) { errors.push("Informe a longitude."); markInvalid("himenopteros-longitude", "Campo obrigatório"); }
        // Data/hora início obrigatória
        if (!val("himenopteros-data_hora_inicio")) { errors.push("Informe a data/hora de início."); markInvalid("himenopteros-data_hora_inicio", "Campo obrigatório"); }
        // Pelo menos uma foto obrigatória
        var fotosInput = document.getElementById("himenopteros_fotos");
        var fotosList = document.querySelectorAll(".js-existing-photo-row");
        if ((!fotosInput || !fotosInput.files || fotosInput.files.length === 0) && fotosList.length === 0) {
          errors.push("Adicione ao menos uma foto do registro.");
          markInvalid("himenopteros_fotos", "Adicione ao menos uma foto");
        }
        // Isolamento de área obrigatório na criação
        var isCreate = !val("himenopteros-id");
        if (isCreate && !val("himenopteros-isolamento_area")) { errors.push("Informe se houve isolamento de área."); markInvalid("himenopteros-isolamento_area", "Campo obrigatório"); }
        if (errors.length) {
          event.preventDefault();
          if (firstInvalid && typeof firstInvalid.focus === "function") firstInvalid.focus();
          return false;
        }
      });
      // Remove marcação ao corrigir
      form.querySelectorAll("input, select, textarea").forEach(function (el) {
        el.addEventListener("input", function () {
          if (el.classList.contains("is-invalid")) {
            el.classList.remove("is-invalid");
            var next = el.nextSibling;
            if (next && next.classList && next.classList.contains("invalid-feedback")) next.remove();
          }
        });
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initHimenopterosForm();
    initHimenopterosList();
  });
})();
