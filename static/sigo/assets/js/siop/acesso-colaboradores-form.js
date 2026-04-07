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

    function getSelectedValues() {
      return Array.from(container.querySelectorAll(".js-colaborador-select"))
        .map(function (select) { return select.value; })
        .filter(Boolean);
    }

    function syncSelectOptions() {
      var selectedValues = getSelectedValues();
      container.querySelectorAll(".js-colaborador-select").forEach(function (select) {
        var currentValue = select.value;
        Array.from(select.options).forEach(function (option) {
          if (!option.value) {
            option.disabled = false;
            return;
          }
          option.disabled = option.value !== currentValue && selectedValues.indexOf(option.value) !== -1;
        });
      });
    }

    function bindRow(row) {
      var select = row.querySelector(".js-colaborador-select");
      var manual = row.querySelector(".js-colaborador-manual");
      if (select) {
        select.addEventListener("change", function () {
          if (select.value && manual) {
            manual.value = "";
          }
          syncSelectOptions();
        });
      }
      if (manual) {
        manual.addEventListener("input", function () {
          if (manual.value.trim() && select) {
            select.value = "";
          }
          syncSelectOptions();
        });
      }
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
      var row = template.content.firstElementChild.cloneNode(true);
      container.appendChild(row);
      bindRow(row);
      syncRemoveButtons();
      syncSelectOptions();
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
      syncSelectOptions();
    });

    container.querySelectorAll(".pessoa-nome-row").forEach(bindRow);
    syncRemoveButtons();
    syncSelectOptions();
  }

  document.addEventListener("DOMContentLoaded", function () {
    initListaPessoas();

    if (!window.SiopAsyncList) {
      return;
    }

    window.SiopAsyncList.initAsyncList({
      formSelector: "#acesso-colaboradores-list-form",
      tableBodySelector: "#acesso-colaboradores-list-body",
      metaSelector: "#acesso-colaboradores-list-meta",
      paginationSelector: "#acesso-colaboradores-pagination",
      columnCount: 7,
      emptyMessage: "Nenhum acesso de colaboradores encontrado para os filtros informados.",
      metaText: function (total) {
        return total + " acesso" + (total === 1 ? "" : "s") + " encontrado" + (total === 1 ? "" : "s") + ".";
      },
      renderRow: function (item) {
        var escapeHtml = window.SiopAsyncList.escapeHtml;
        var pessoas = buildResumo((item.pessoas || []).map(function (pessoa) { return pessoa.nome || ""; }).filter(Boolean));
        var badgeClass = item.status === "concluído" || item.status === "concluido" ? "badge badge-success" : "badge badge-warning";
        return (
          "<tr>" +
          "<td>#" + item.id + "</td>" +
          '<td><span title="' + escapeHtml(pessoas.title) + '">' + escapeHtml(pessoas.resumo) + "</span></td>" +
          "<td>" + escapeHtml(item.p1_label || item.p1 || "-") + "</td>" +
          "<td>" + escapeHtml(item.unidade_sigla || "-") + "</td>" +
          "<td>" + escapeHtml(item.entrada || "-") + "</td>" +
          '<td><span class="' + badgeClass + '">' + escapeHtml(item.status_label || "-") + "</span></td>" +
          '<td class="text-end"><a href="' + escapeHtml(item.view_url || "#") + '" class="btn btn-sm btn-primary">Abrir</a></td>' +
          "</tr>"
        );
      },
    });
  });
})();
