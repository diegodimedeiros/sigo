(function () {
  function initBombeiros() {
    var bc1 = document.getElementById("id_bombeiro_civil");
    var bc2 = document.getElementById("id_bombeiro_civil_2");
    if (!bc1 || !bc2) {
      return;
    }

    function snapshot(select) {
      return Array.from(select.options).map(function (option) {
        return {
          value: option.value,
          label: option.textContent,
          selected: option.selected,
        };
      });
    }

    var bc1Options = snapshot(bc1);
    var bc2Options = snapshot(bc2);

    function rebuild(select, options, blockedValue, preferredValue) {
      select.innerHTML = "";
      options.forEach(function (option) {
        if (option.value && option.value === blockedValue) {
          return;
        }
        var node = document.createElement("option");
        node.value = option.value;
        node.textContent = option.label;
        node.selected = option.value === preferredValue;
        select.appendChild(node);
      });
      if (!Array.from(select.options).some(function (option) { return option.value === preferredValue; })) {
        select.value = "";
      }
    }

    function syncBcSelects() {
      rebuild(bc1, bc1Options, bc2.value, bc1.value);
      rebuild(bc2, bc2Options, bc1.value, bc2.value);
    }

    bc1.addEventListener("change", syncBcSelects);
    bc2.addEventListener("change", syncBcSelects);
    syncBcSelects();
  }

  document.addEventListener("DOMContentLoaded", function () {
    initBombeiros();

    if (!window.SiopAsyncList) {
      return;
    }

    window.SiopAsyncList.initAsyncList({
      formSelector: "#efetivo-list-form",
      tableBodySelector: "#efetivo-list-body",
      metaSelector: "#efetivo-list-meta",
      paginationSelector: "#efetivo-pagination",
      columnCount: 6,
      emptyMessage: "Nenhum registro encontrado.",
      metaText: function (total) {
        return total + " registro" + (total === 1 ? "" : "s") + " encontrado" + (total === 1 ? "" : "s") + ".";
      },
      renderRow: function (item) {
        var escapeHtml = window.SiopAsyncList.escapeHtml;
        return (
          "<tr>" +
          "<td>#" + item.id + "</td>" +
          "<td>" + escapeHtml(item.plantao || "-") + "</td>" +
          "<td>" + escapeHtml(item.criado_em || "-") + "</td>" +
          "<td>" + escapeHtml(item.criado_por || "-") + "</td>" +
          "<td>" + escapeHtml(item.modificado_em || "-") + "</td>" +
          '<td class="text-end"><a href="' + escapeHtml(item.view_url || "#") + '" class="btn btn-sm btn-label-info">Ver</a></td>' +
          "</tr>"
        );
      },
    });
  });
})();
