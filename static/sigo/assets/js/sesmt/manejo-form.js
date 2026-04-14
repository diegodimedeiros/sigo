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

  function initPhotoManager(config) {
    var input = document.getElementById(config.inputId);
    var status = document.getElementById(config.statusId);
    var listNode = document.getElementById(config.listId);
    var emptyNode = document.getElementById(config.emptyId);
    if (!input || !status || !listNode || !emptyNode) return;

    var files = Array.from(input.files || []);

    function createTransfer(currentFiles) {
      var transfer = new DataTransfer();
      currentFiles.forEach(function (file) {
        transfer.items.add(file);
      });
      return transfer.files;
    }

    function fileSignature(file) {
      return [file.name, file.size, file.lastModified, file.type].join("::");
    }

    function syncInput() {
      input.files = createTransfer(files);
    }

    function refresh() {
      syncInput();
      status.textContent = files.length ? files.length + " ficheiro(s) selecionado(s)" : "Nenhum ficheiro selecionado";
      listNode.innerHTML = "";
      emptyNode.style.display = files.length ? "none" : "";
      files.forEach(function (file, index) {
        var row = document.createElement("div");
        row.className = "small border rounded-2 px-3 py-2 d-flex align-items-center justify-content-between gap-3";

        var label = document.createElement("div");
        label.className = "text-truncate";
        label.textContent = file.name;

        var removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.className = "btn btn-sm btn-label-danger";
        removeButton.textContent = "X";
        removeButton.addEventListener("click", function () {
          files = files.filter(function (_item, currentIndex) { return currentIndex !== index; });
          refresh();
        });

        row.appendChild(label);
        row.appendChild(removeButton);
        listNode.appendChild(row);
      });
    }

    input.addEventListener("change", function () {
      var incoming = Array.from(input.files || []);
      incoming.forEach(function (file) {
        var signature = fileSignature(file);
        var exists = files.some(function (current) { return fileSignature(current) === signature; });
        if (!exists) files.push(file);
      });
      refresh();
      if (typeof config.onChange === "function") {
        config.onChange();
      }
    });

    refresh();
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
    if (!container || !emptyNode) return;
    emptyNode.style.display = "none";
    container.innerHTML =
      '<div class="detail-note-box">Latitude: ' + latitude + " | Longitude: " + longitude +
      (hash ? " | Hash: " + hash : "") + "</div>";
  }

  function renderGeolocationError(container, emptyNode, message) {
    if (!container || !emptyNode) return;
    container.innerHTML = "";
    emptyNode.style.display = "";
    emptyNode.textContent = message;
  }

  function syncGeolocation(kind, options) {
    var latInput = document.getElementById("latitude_" + kind);
    var lonInput = document.getElementById("longitude_" + kind);
    var container = document.getElementById("geolocalizacao_" + kind);
    var emptyNode = document.getElementById("geolocalizacao_" + kind + "_vazia");
    if (!latInput || !lonInput || !container || !emptyNode) return;

    function renderCurrent() {
      if ((latInput.value || "").trim() && (lonInput.value || "").trim()) {
        renderGeolocation(container, emptyNode, latInput.value, lonInput.value, "");
      } else {
        renderGeolocationError(container, emptyNode, "Nenhuma geolocalização registrada ainda.");
      }
    }

    function capture() {
      if (!navigator.geolocation) {
        renderGeolocationError(container, emptyNode, "Geolocalização indisponível neste dispositivo.");
        return;
      }
      renderGeolocationError(container, emptyNode, "Obtendo geolocalização...");
      navigator.geolocation.getCurrentPosition(
        function (position) {
          latInput.value = Number(position.coords.latitude).toFixed(7);
          lonInput.value = Number(position.coords.longitude).toFixed(7);
          renderCurrent();
        },
        function () {
          renderGeolocationError(container, emptyNode, "Não foi possível obter a localização.");
        },
        {
          enableHighAccuracy: true,
          maximumAge: 10000,
          timeout: 15000
        }
      );
    }

    if ((options || {}).autoCapture) {
      capture();
    } else {
      renderCurrent();
    }

    return {
      capture: capture,
      renderCurrent: renderCurrent
    };
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

    var capturaGeo = syncGeolocation("captura", { autoCapture: !(document.getElementById("latitude_captura").value || "").trim() });
    var solturaGeo = syncGeolocation("soltura", { autoCapture: false });

    var realizadoField = document.getElementById("realizado_manejo");
    if (realizadoField && solturaGeo) {
      realizadoField.addEventListener("change", function () {
        syncToggleFields();
        if (isTruthyValue(realizadoField.value) && !(document.getElementById("latitude_soltura").value || "").trim()) {
          solturaGeo.capture();
        }
      });
    }

    initPhotoManager({
      inputId: "foto_captura",
      statusId: "foto_captura_status",
      listId: "lista_fotos_captura",
      emptyId: "lista_fotos_captura_vazia",
      onChange: function () {
        if (capturaGeo) capturaGeo.capture();
      }
    });
    initPhotoManager({
      inputId: "foto_soltura",
      statusId: "foto_soltura_status",
      listId: "lista_fotos_soltura",
      emptyId: "lista_fotos_soltura_vazia",
      onChange: function () {
        if (solturaGeo) solturaGeo.capture();
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initManejoForm();
    initManejoList();
  });
})();
