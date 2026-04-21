(function () {
  function requestCatalog(url, queryParam, queryValue) {
    if (window.ReportosCatalogos && (queryParam === "area" || queryParam === "classe")) {
      var catalogPromise = queryParam === "classe"
        ? window.ReportosCatalogos.getEspeciesAsync(queryValue)
        : window.ReportosCatalogos.getLocaisAsync(queryValue);
      return catalogPromise.then(function (cached) {
        if (cached !== null) {
          var dataKey = queryParam === "classe" ? "especies" : "locais";
          var resData = {};
          resData[dataKey] = cached;
          return { ok: true, data: resData };
        }

        var fetchFn = (window.SigoCsrf && typeof window.SigoCsrf.fetch === "function")
          ? window.SigoCsrf.fetch.bind(window.SigoCsrf)
          : window.fetch.bind(window);
        var fullUrl = new URL(url, window.location.origin);
        fullUrl.searchParams.set(queryParam, queryValue);
        return fetchFn(fullUrl.toString(), {
          headers: { "X-Requested-With": "XMLHttpRequest" }
        }).then(function (response) {
          if (!response.ok) throw new Error("Falha ao carregar catálogo.");
          return response.json();
        });
      });
    }

    var fetchFn = (window.SigoCsrf && typeof window.SigoCsrf.fetch === "function")
      ? window.SigoCsrf.fetch.bind(window.SigoCsrf)
      : window.fetch.bind(window);
    var fullUrl = new URL(url, window.location.origin);
    fullUrl.searchParams.set(queryParam, queryValue);
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
      emptyMessage: "Nenhum registro encontrado.",
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

    // Validação required frontend (espelhando regras do backend)
    form.addEventListener("submit", function (event) {
      var errors = [];
      var firstInvalid = null;
      function markInvalidByName(name, msg) {
        var el = form.querySelector('[name="' + name + '"]');
        if (!el) return;
        el.classList.add("is-invalid");
        var msgNode = document.createElement("div");
        msgNode.className = "invalid-feedback";
        msgNode.textContent = msg;
        if (el.nextSibling) el.parentNode.insertBefore(msgNode, el.nextSibling);
        else el.parentNode.appendChild(msgNode);
        if (!firstInvalid) firstInvalid = el;
      }
      function valByName(name) {
        var el = form.querySelector('[name="' + name + '"]');
        return el && el.value ? el.value.trim() : "";
      }
      // Limpa marcações antigas
      form.querySelectorAll(".is-invalid").forEach(function (el) { el.classList.remove("is-invalid"); });
      form.querySelectorAll(".invalid-feedback").forEach(function (el) { el.remove(); });

      // Data/hora obrigatória
      if (!valByName("data_hora")) { errors.push("Informe a data/hora do manejo."); markInvalidByName("data_hora", "Campo obrigatório"); }

      // Classe obrigatória
      if (!valByName("classe")) { errors.push("Selecione a classe."); markInvalidByName("classe", "Campo obrigatório"); }

      // Nome popular obrigatório
      if (!valByName("nome_popular")) { errors.push("Selecione o nome popular."); markInvalidByName("nome_popular", "Campo obrigatório"); }

      // Área de captura obrigatória
      if (!valByName("area_captura")) { errors.push("Selecione a área de captura."); markInvalidByName("area_captura", "Campo obrigatório"); }

      // Local de captura obrigatório
      if (!valByName("local_captura")) { errors.push("Selecione o local de captura."); markInvalidByName("local_captura", "Campo obrigatório"); }

      // Descrição do local obrigatória
      if (!valByName("descricao_local")) { errors.push("Informe a descrição do local."); markInvalidByName("descricao_local", "Campo obrigatório"); }

      // Foto de captura obrigatória
      var fotosInput = document.getElementById("foto_captura");
      var fotosList = document.querySelectorAll("#lista_fotos_captura .js-existing-photo-row");
      if ((!fotosInput || !fotosInput.files || fotosInput.files.length === 0) && fotosList.length === 0) {
        errors.push("Adicione ao menos uma foto de captura.");
        markInvalidByName("foto_captura", "Adicione ao menos uma foto");
      }

      // Latitude e longitude de captura obrigatórios
      if (!valByName("latitude_captura")) { errors.push("Informe a latitude da captura."); markInvalidByName("latitude_captura", "Campo obrigatório"); }
      if (!valByName("longitude_captura")) { errors.push("Informe a longitude da captura."); markInvalidByName("longitude_captura", "Campo obrigatório"); }

      // Se realizado manejo, validar campos de soltura
      var realizado = form.querySelector('[name="realizado_manejo"]');
      if (realizado && (realizado.checked || realizado.value === "true" || realizado.value === "1")) {
        // Área de soltura obrigatória
        if (!valByName("area_soltura")) { errors.push("Selecione a área de soltura."); markInvalidByName("area_soltura", "Campo obrigatório"); }
        // Local de soltura obrigatória
        if (!valByName("local_soltura")) { errors.push("Selecione o local de soltura."); markInvalidByName("local_soltura", "Campo obrigatório"); }
        // Descrição do local de soltura obrigatória
        if (!valByName("descricao_local_soltura")) { errors.push("Informe a descrição do local de soltura."); markInvalidByName("descricao_local_soltura", "Campo obrigatório"); }
        // Foto de soltura obrigatória
        var fotosSolturaInput = document.getElementById("foto_soltura");
        var fotosSolturaList = document.querySelectorAll("#lista_fotos_soltura .js-existing-photo-row");
        if ((!fotosSolturaInput || !fotosSolturaInput.files || fotosSolturaInput.files.length === 0) && fotosSolturaList.length === 0) {
          errors.push("Adicione ao menos uma foto de soltura.");
          markInvalidByName("foto_soltura", "Adicione ao menos uma foto");
        }
        // Latitude e longitude de soltura obrigatórios
        if (!valByName("latitude_soltura")) { errors.push("Informe a latitude da soltura."); markInvalidByName("latitude_soltura", "Campo obrigatório"); }
        if (!valByName("longitude_soltura")) { errors.push("Informe a longitude da soltura."); markInvalidByName("longitude_soltura", "Campo obrigatório"); }
      }

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
