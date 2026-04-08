(function () {
  function buildResumo(values) {
    if (!values.length) {
      return { resumo: "-", title: "" };
    }
    if (values.length === 1) {
      return { resumo: values[0], title: values[0] };
    }
    return {
      resumo: values[0] + " +" + (values.length - 1),
      title: values.join(", "),
    };
  }

  function initListaPessoas() {
    var container = document.getElementById("pessoas-container");
    var addButton = document.getElementById("add-pessoa-btn");
    var template = document.getElementById("pessoa-nome-template");
    if (!container || !addButton || !template) {
      return;
    }

    function syncRemoveButtons() {
      var rows = container.querySelectorAll(".pessoa-nome-row");
      rows.forEach(function (row, index) {
        var button = row.querySelector(".pessoa-remove-btn");
        if (!button) {
          return;
        }
        button.style.display = rows.length === 1 && index === 0 ? "none" : "";
      });
    }

    addButton.addEventListener("click", function () {
      container.appendChild(template.content.firstElementChild.cloneNode(true));
      syncRemoveButtons();
    });

    container.addEventListener("click", function (event) {
      if (!event.target.classList.contains("pessoa-remove-btn")) {
        return;
      }
      var row = event.target.closest(".pessoa-nome-row");
      if (row) {
        row.remove();
      }
      syncRemoveButtons();
    });

    syncRemoveButtons();
  }

  async function submitChegada(form) {
    if (!form || !window.SigoCsrf) {
      return;
    }

    var feedback = form.querySelector(".js-form-feedback");
    var submitButton = form.querySelector('[type="submit"]');
    var originalLabel = submitButton ? submitButton.textContent : "";

    if (feedback) {
      feedback.className = "alert alert-danger d-none js-form-feedback";
      feedback.textContent = "";
    }

    if (submitButton) {
      submitButton.disabled = true;
      submitButton.textContent = "Registrando...";
    }

    try {
      var response = await window.SigoCsrf.fetch(form.dataset.apiUrl, {
        method: "POST",
        body: new FormData(form),
      });
      var payload = await response.json();
      if (response.ok && payload.ok) {
        window.location.reload();
        return;
      }
      var error = payload.error || {};
      if (feedback) {
        feedback.className = "alert alert-danger js-form-feedback";
        feedback.textContent = error.message || "Não foi possível registrar a chegada.";
        feedback.classList.remove("d-none");
      }
    } catch (_error) {
      if (feedback) {
        feedback.className = "alert alert-danger js-form-feedback";
        feedback.textContent = "Erro ao registrar a chegada. Tente novamente.";
        feedback.classList.remove("d-none");
      }
    } finally {
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = originalLabel;
      }
    }
  }

  function initRegistrarChegada() {
    var form = document.getElementById("registrar-chegada-form");
    if (!form) {
      return;
    }

    var actionInput = document.getElementById("id_chegada_acao");
    var pessoaInput = document.getElementById("id_pessoa_id");
    var label = document.getElementById("registrar-chegada-label");
    var cancelButton = document.getElementById("cancelar-chegada-btn");

    document.querySelectorAll(".registrar-chegada-btn").forEach(function (button) {
      button.addEventListener("click", function () {
        actionInput.value = button.dataset.chegadaAcao;
        pessoaInput.value = button.dataset.pessoaId || "";
        label.textContent = "Registrar chegada para " + button.dataset.pessoaNome;
        form.classList.remove("d-none");
        form.scrollIntoView({ behavior: "smooth", block: "nearest" });
      });
    });

    cancelButton.addEventListener("click", function () {
      form.classList.add("d-none");
    });

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      submitChegada(form);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initListaPessoas();
    initRegistrarChegada();

    if (!window.SiopAsyncList) {
      return;
    }

    window.SiopAsyncList.initAsyncList({
      formSelector: "#liberacao-acesso-list-form",
      tableBodySelector: "#liberacao-acesso-list-body",
      metaSelector: "#liberacao-acesso-list-meta",
      paginationSelector: "#liberacao-acesso-pagination",
      columnCount: 8,
      emptyMessage: "Nenhuma liberação de acesso encontrada para os filtros informados.",
      metaText: function (total) {
        return total + " liberação" + (total === 1 ? "" : "ões") + " encontrada" + (total === 1 ? "" : "s") + ".";
      },
      renderRow: function (item) {
        var escapeHtml = window.SiopAsyncList.escapeHtml;
        var pessoas = buildResumo((item.pessoas || []).map(function (pessoa) { return pessoa.nome || ""; }).filter(Boolean));
        var documentos = buildResumo((item.pessoas || []).map(function (pessoa) { return pessoa.documento || ""; }).filter(Boolean));
        return (
          "<tr>" +
          "<td>#" + item.id + "</td>" +
          '<td><span title="' + escapeHtml(pessoas.title) + '">' + escapeHtml(pessoas.resumo) + "</span></td>" +
          '<td><span title="' + escapeHtml(documentos.title) + '">' + escapeHtml(documentos.resumo) + "</span></td>" +
          "<td>" + escapeHtml(item.empresa || "-") + "</td>" +
          "<td>" + escapeHtml(item.solicitante || "-") + "</td>" +
          "<td>" + escapeHtml(item.unidade_sigla || "-") + "</td>" +
          "<td>" + escapeHtml(item.data_liberacao || "-") + "</td>" +
          '<td class="text-end"><a href="' + escapeHtml(item.view_url || "#") + '" class="btn btn-sm btn-label-info">Ver</a></td>' +
          "</tr>"
        );
      },
    });
  });
})();
