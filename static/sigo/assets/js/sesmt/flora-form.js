(function () {
  function requestCatalog(url, queryParam, queryValue) {
    if (window.ReportosCatalogos && queryParam === "area") {
      return window.ReportosCatalogos.getLocaisAsync(queryValue).then(function (cached) {
        if (cached !== null) {
          return { ok: true, data: { locais: cached } };
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

  function triggerFileButtons() {
    document.querySelectorAll("[data-trigger-file]").forEach(function (button) {
      button.addEventListener("click", function () {
        var input = document.getElementById(button.dataset.triggerFile || "");
        if (input) input.click();
      });
    });
  }

  function syncAreaLocais() {
    var area = document.getElementById("flora-area");
    var local = document.getElementById("flora-local");
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
        .catch(function () {
          buildOptions(local, [], "Selecione");
    
      // Validação required frontend (espelhando regras do backend)
      form.addEventListener("submit", function (event) {
        var submitBtn = document.getElementById("flora-submit-btn");
        if (submitBtn) submitBtn.disabled = true;
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

        // Latitude e longitude obrigatórios
        if (!valByName("latitude")) { errors.push("Informe a latitude."); markInvalidByName("latitude", "Campo obrigatório"); }
        if (!valByName("longitude")) { errors.push("Informe a longitude."); markInvalidByName("longitude", "Campo obrigatório"); }

        // Data/hora início obrigatória
        if (!valByName("data_hora_inicio")) { errors.push("Informe a data/hora de início."); markInvalidByName("data_hora_inicio", "Campo obrigatório"); }

        // Responsável pelo registro obrigatório
        if (!valByName("responsavel_registro")) { errors.push("Selecione o responsável pelo registro."); markInvalidByName("responsavel_registro", "Campo obrigatório"); }

        // Área obrigatória
        if (!valByName("area")) { errors.push("Selecione a área."); markInvalidByName("area", "Campo obrigatório"); }

        // Local obrigatório
        if (!valByName("local")) { errors.push("Selecione o local."); markInvalidByName("local", "Campo obrigatório"); }

        // Condição obrigatória
        if (!valByName("condicao")) { errors.push("Selecione a condição."); markInvalidByName("condicao", "Campo obrigatório"); }

        // Justificativa obrigatória
        if (!valByName("justificativa")) { errors.push("Informe a justificativa para registro."); markInvalidByName("justificativa", "Campo obrigatório"); }

        // Isolamento de área obrigatório
        if (!valByName("isolamento_area")) { errors.push("Informe se houve isolamento de área."); markInvalidByName("isolamento_area", "Campo obrigatório"); }

        // Foto antes obrigatória
        var fotosInput = document.getElementById("foto_antes");
        var fotosList = document.querySelectorAll("#lista_foto_antes .js-existing-photo-row");
        if ((!fotosInput || !fotosInput.files || fotosInput.files.length === 0) && fotosList.length === 0) {
          errors.push("Adicione ao menos uma foto de antes.");
          markInvalidByName("foto_antes", "Adicione ao menos uma foto");
        }

        // Se ação realizada preenchida, descrição obrigatória
        var acaoRealizada = valByName("acao_realizada");
        var descricao = valByName("descricao");
        if (acaoRealizada && !descricao) {
          errors.push("Informe a descrição da ação realizada.");
          markInvalidByName("descricao", "Campo obrigatório se ação realizada");
        }

        // Diâmetro do peito, se preenchido, deve ser > 0
        var diametroPeito = valByName("diametro_peito");
        if (diametroPeito && parseFloat(diametroPeito) <= 0) {
          errors.push("O diâmetro à altura do peito deve ser maior que zero.");
          markInvalidByName("diametro_peito", "Valor deve ser maior que zero");
        }

        // Altura total, se preenchida, deve ser > 0
        var alturaTotal = valByName("altura_total");
        if (alturaTotal && parseFloat(alturaTotal) <= 0) {
          errors.push("A altura total deve ser maior que zero.");
          markInvalidByName("altura_total", "Valor deve ser maior que zero");
        }

        if (errors.length) {
          event.preventDefault();
          if (submitBtn) submitBtn.disabled = false;
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
        });
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

  function renderGeolocation(container, emptyNode, latitude, longitude, hash) {
    window.SesmtGeolocation.render(container, emptyNode, latitude, longitude, hash);
  }

  function renderGeolocationError(container, emptyNode, message) {
    container.innerHTML = "";
    emptyNode.style.display = "";
    emptyNode.textContent = message;
  }

  function initFloraList() {
    if (!window.SiopAsyncList || typeof window.SiopAsyncList.initAsyncList !== "function") return;
    if (!document.getElementById("flora-list-form")) return;
    window.SiopAsyncList.initAsyncList({
      formSelector: "#flora-list-form",
      tableBodySelector: "#flora-list-body",
      metaSelector: "#flora-list-meta",
      paginationSelector: "#flora-list-pagination",
      dataKey: "registros",
      columnCount: 7,
      loadingText: "Carregando registros de flora...",
      emptyMessage: "Nenhum registro encontrado.",
      metaText: function (total) {
        return total + " registro" + (total === 1 ? "" : "s") + " encontrado" + (total === 1 ? "" : "s") + ".";
      },
      renderRow: function (item) {
        return (
          "<tr>" +
          "<td>#"+ window.SiopAsyncList.escapeHtml(item.id) +"</td>" +
          "<td>"+ window.SiopAsyncList.escapeHtml(item.data) +"</td>" +
          "<td>"+ window.SiopAsyncList.escapeHtml(item.popular) +"</td>" +
          "<td>"+ window.SiopAsyncList.escapeHtml(item.especie) +"</td>" +
          "<td>"+ window.SiopAsyncList.escapeHtml(item.area) +"</td>" +
          '<td><span class="badge badge-' + window.SiopAsyncList.escapeHtml(item.status_badge) + '">' + window.SiopAsyncList.escapeHtml(item.status_label) + "</span></td>" +
          '<td class="text-end"><a href="' + window.SiopAsyncList.escapeHtml(item.view_url) + '" class="btn btn-sm btn-label-info">Ver</a></td>' +
          "</tr>"
        );
      }
    });
  }

  function initFloraForm() {
    var form = document.getElementById("flora-form");
    if (!form) return;

    triggerFileButtons();
    syncAreaLocais();
    initExistingPhotoRemoval(form);

    window.SesmtPhotoManager.init({
      inputId: "foto_antes",
      statusId: "foto_antes_status",
      listId: "lista_foto_antes",
      emptyId: "lista_foto_antes_vazia"
    });

    window.SesmtPhotoManager.init({
      inputId: "foto_depois",
      statusId: "foto_depois_status",
      listId: "lista_foto_depois",
      emptyId: "lista_foto_depois_vazia"
    });

    window.SesmtGeolocation.initCapture({
      latitudeId: "flora-latitude",
      longitudeId: "flora-longitude",
      containerId: "geolocalizacao_flora",
      emptyNodeId: "geolocalizacao_flora_vazia"
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initFloraForm();
    initFloraList();
  });
})();
