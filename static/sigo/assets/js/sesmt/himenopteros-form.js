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

  function initPhotoManager(config) {
    var input = document.getElementById(config.inputId);
    var status = document.getElementById(config.statusId);
    var listNode = document.getElementById(config.listId);
    var emptyNode = document.getElementById(config.emptyId);
    if (!input || !status || !listNode || !emptyNode) return;
    var files = Array.from(input.files || []);
    function createTransfer(currentFiles) {
      var transfer = new DataTransfer();
      currentFiles.forEach(function (file) { transfer.items.add(file); });
      return transfer.files;
    }
    function signature(file) {
      return [file.name, file.size, file.lastModified, file.type].join("::");
    }
    function refresh() {
      input.files = createTransfer(files);
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
      Array.from(input.files || []).forEach(function (file) {
        var exists = files.some(function (current) { return signature(current) === signature(file); });
        if (!exists) files.push(file);
      });
      refresh();
      if (typeof config.onChange === "function") config.onChange();
    });
    refresh();
  }

  function renderGeolocation(container, emptyNode, latitude, longitude) {
    emptyNode.style.display = "none";
    var div = document.createElement("div");
    div.className = "detail-note-box";
    div.textContent = "Latitude: " + latitude + " | Longitude: " + longitude;
    container.innerHTML = "";
    container.appendChild(div);
  }

  function renderGeolocationError(container, emptyNode, message) {
    container.innerHTML = "";
    emptyNode.style.display = "";
    emptyNode.textContent = message;
  }

  function syncGeolocation() {
    var latInput = document.getElementById("himenopteros-latitude");
    var lonInput = document.getElementById("himenopteros-longitude");
    var container = document.getElementById("geolocalizacao_himenopteros");
    var emptyNode = document.getElementById("geolocalizacao_himenopteros_vazia");
    if (!latInput || !lonInput || !container || !emptyNode) return null;
    function renderCurrent() {
      if ((latInput.value || "").trim() && (lonInput.value || "").trim()) {
        renderGeolocation(container, emptyNode, latInput.value, lonInput.value);
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
      navigator.geolocation.getCurrentPosition(function (position) {
        latInput.value = Number(position.coords.latitude).toFixed(7);
        lonInput.value = Number(position.coords.longitude).toFixed(7);
        renderCurrent();
      }, function () {
        renderGeolocationError(container, emptyNode, "Não foi possível obter a localização.");
      }, { enableHighAccuracy: true, maximumAge: 10000, timeout: 15000 });
    }
    if (!(latInput.value || "").trim()) {
      capture();
    } else {
      renderCurrent();
    }
    return { capture: capture, renderCurrent: renderCurrent };
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
      emptyMessage: "Nenhum registro de himenóptero encontrado.",
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
    var geo = syncGeolocation();
    initPhotoManager({
      inputId: "himenopteros_fotos",
      statusId: "himenopteros_fotos_status",
      listId: "lista_himenopteros_fotos",
      emptyId: "lista_himenopteros_fotos_vazia",
      onChange: function () { if (geo) geo.capture(); }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initHimenopterosForm();
    initHimenopterosList();
  });
})();
