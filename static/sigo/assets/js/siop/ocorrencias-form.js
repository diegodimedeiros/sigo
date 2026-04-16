(function () {
  function buildOptions(target, values, placeholder) {
    if (!target) return;

    if (target.tagName === "SELECT") {
      target.innerHTML = "";
      var firstOption = document.createElement("option");
      firstOption.value = "";
      firstOption.textContent = placeholder;
      target.appendChild(firstOption);

      values.forEach(function (value) {
        var optionValue = typeof value === "object" && value !== null ? value.chave : value;
        var optionLabel = typeof value === "object" && value !== null ? value.valor : value;
        var option = document.createElement("option");
        option.value = optionValue;
        option.textContent = optionLabel;
        target.appendChild(option);
      });
      return;
    }

    if (target.tagName === "DATALIST") {
      target.innerHTML = "";
      values.forEach(function (value) {
        var option = document.createElement("option");
        option.value = value;
        target.appendChild(option);
      });
    }
  }

  function requestCatalog(url, queryParam, queryValue) {
    var fullUrl = new URL(url, window.location.origin);
    fullUrl.searchParams.set(queryParam, queryValue);
    return fetch(fullUrl.toString(), {
      headers: {
        "X-Requested-With": "XMLHttpRequest"
      }
    }).then(function (response) {
      if (!response.ok) {
        throw new Error("Falha ao carregar catálogo.");
      }
      return response.json();
    });
  }

  function clearFieldErrors(form) {
    form.querySelectorAll(".field-error").forEach(function (node) {
      node.textContent = "";
      node.classList.add("d-none");
    });
  }

  function renderFieldErrors(form, details) {
    Object.entries(details || {}).forEach(function (entry) {
      var fieldName = entry[0];
      var messages = entry[1];
      var target = form.querySelector('[data-field-error="' + fieldName + '"]');
      if (!target) return;
      var normalized = Array.isArray(messages) ? messages.join(" ") : String(messages || "");
      target.textContent = normalized;
      target.classList.remove("d-none");
    });
  }

  function showFormFeedback(message, type) {
    var box = document.getElementById("ocorrencia-form-feedback");
    if (!box) return;
    box.className = "alert alert-" + (type || "danger");
    box.textContent = message;
    box.classList.remove("d-none");
  }

  function hideFormFeedback() {
    var box = document.getElementById("ocorrencia-form-feedback");
    if (!box) return;
    box.className = "alert alert-danger d-none";
    box.textContent = "";
  }

  function initOcorrenciasSubmit() {
    var form = document.getElementById("ocorrencia-form");
    if (!form || typeof window.SigoCsrf === "undefined") {
      return;
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      hideFormFeedback();
      clearFieldErrors(form);

      var submitButton = form.querySelector('[type="submit"]');
      var originalLabel = submitButton ? submitButton.textContent : "";
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "Salvando...";
      }

      window.SigoCsrf.fetch(form.dataset.apiUrl || form.action || window.location.pathname, {
        method: "POST",
        body: new FormData(form)
      })
        .then(function (response) {
          return response.json().then(function (payload) {
            return { response: response, payload: payload };
          });
        })
        .then(function (result) {
          var payload = result.payload || {};
          if (result.response.ok && payload.ok) {
            var redirectUrl = ((payload.data || {}).redirect_url) || ((payload.data || {}).view_url);
            if (redirectUrl) {
              window.location.href = redirectUrl;
              return;
            }
            showFormFeedback(payload.message || "Ocorrência salva com sucesso.", "success");
            form.reset();
            return;
          }

          var error = payload.error || {};
          renderFieldErrors(form, error.details || {});
          showFormFeedback(error.message || "Não foi possível salvar a ocorrência.", "danger");
        })
        .catch(function () {
          showFormFeedback("Erro ao enviar a ocorrência. Tente novamente.", "danger");
        })
        .finally(function () {
          if (submitButton) {
            submitButton.disabled = false;
            submitButton.textContent = originalLabel;
          }
        });
    });
  }

  function initOcorrenciasForm() {
    var areaField = document.getElementById("area");
    var localField = document.getElementById("local");
    var naturezaField = document.getElementById("natureza");
    var tipoField = document.getElementById("tipo");

    if (areaField && localField) {
      var locaisUrl = areaField.dataset.locaisUrl;
      var currentLocal = localField.dataset.selectedValue || localField.value;

      var syncLocais = function () {
        var area = areaField.value;
        if (!locaisUrl || !area) {
          buildOptions(localField, [], "Selecione a área primeiro...");
          return;
        }

        requestCatalog(locaisUrl, "area", area)
          .then(function (payload) {
            var locais = (((payload || {}).data || {}).locais) || [];
            buildOptions(localField, locais, "Selecione");

            if (currentLocal && locais.some(function (item) { return item.chave === currentLocal; })) {
              localField.value = currentLocal;
            } else if (localField.value && !locais.some(function (item) { return item.chave === localField.value; })) {
              localField.value = "";
            }
          })
          .catch(function () {
            buildOptions(localField, [], "Selecione a área primeiro...");
          });
      };

      areaField.addEventListener("change", function () {
        currentLocal = "";
        syncLocais();
      });
      syncLocais();
    }

    if (naturezaField && tipoField) {
      var tiposUrl = naturezaField.dataset.tiposUrl;
      var currentTipo = tipoField.dataset.selectedValue || tipoField.value;

      var syncTipos = function () {
        var natureza = naturezaField.value;
        if (!tiposUrl || !natureza) {
          buildOptions(tipoField, [], "Selecione");
          return;
        }

        requestCatalog(tiposUrl, "natureza", natureza)
          .then(function (payload) {
            var tipos = (((payload || {}).data || {}).tipos) || [];
            buildOptions(tipoField, tipos, "Selecione");

            if (currentTipo && tipos.some(function (item) { return item.chave === currentTipo; })) {
              tipoField.value = currentTipo;
            } else if (tipoField.value && !tipos.some(function (item) { return item.chave === tipoField.value; })) {
              tipoField.value = "";
            }
          })
          .catch(function () {
            buildOptions(tipoField, [], "Selecione");
          });
      };

      naturezaField.addEventListener("change", function () {
        currentTipo = "";
        syncTipos();
      });
      syncTipos();
    }

    initOcorrenciasSubmit();

    if (window.SiopAsyncList) {
      window.SiopAsyncList.initAsyncList({
        formSelector: "#ocorrencias-list-form",
        tableBodySelector: "#ocorrencias-list-body",
        metaSelector: "#ocorrencias-list-meta",
        paginationSelector: "#ocorrencias-list-pagination",
        dataKey: "ocorrencias",
        columnCount: 8,
        emptyMessage: "Nenhum registro encontrado.",
        metaText: function (total) {
          return total + " registro" + (total === 1 ? "" : "s") + " encontrado" + (total === 1 ? "" : "s") + ".";
        },
        renderRow: function (item) {
          var escapeHtml = window.SiopAsyncList.escapeHtml;
          var statusHtml = item.status
            ? '<span class="badge badge-success">Finalizada</span>'
            : '<span class="badge badge-warning">Em aberto</span>';
          return (
            "<tr>" +
            "<td>#" + item.id + "</td>" +
            "<td>" + escapeHtml(item.data || "-") + "</td>" +
            "<td>" + escapeHtml(item.pessoa || "-") + "</td>" +
            "<td>" + escapeHtml(item.natureza || "-") + "</td>" +
            "<td>" + escapeHtml(item.tipo || "-") + "</td>" +
            "<td>" + escapeHtml(item.area || "-") + "</td>" +
            "<td>" + statusHtml + "</td>" +
            '<td class="text-end"><a href="' + escapeHtml(item.view_url || "#") + '" class="btn btn-sm btn-label-info">Ver</a></td>' +
            "</tr>"
          );
        }
      });
    }
  }

  document.addEventListener("DOMContentLoaded", initOcorrenciasForm);
})();
