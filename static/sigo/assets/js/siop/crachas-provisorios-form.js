(function () {
  function badgeClass(status) {
    return status === "devolvido" ? "badge badge-success" : "badge badge-warning";
  }

  document.addEventListener("DOMContentLoaded", function () {
    var form = document.querySelector('form[data-async-form="true"]');
    if (!form || !window.SiopAsyncForm) {
      form = null;
    }
    if (form && window.SiopAsyncForm) {
      window.SiopAsyncForm.submitAsyncForm(form);
    }

    if (!window.SiopAsyncList) {
      return;
    }

    window.SiopAsyncList.initAsyncList({
      formSelector: "#crachas-provisorios-list-form",
      tableBodySelector: "#crachas-provisorios-list-body",
      metaSelector: "#crachas-provisorios-list-meta",
      paginationSelector: "#crachas-provisorios-pagination",
      columnCount: 9,
      emptyMessage: "Nenhum registro encontrado.",
      metaText: function (total) {
        return total + " crachá" + (total === 1 ? "" : "s") + " encontrado" + (total === 1 ? "" : "s") + ".";
      },
      renderRow: function (item) {
        var escapeHtml = window.SiopAsyncList.escapeHtml;
        return (
          "<tr>" +
          "<td>#" + item.id + "</td>" +
          "<td>" + escapeHtml(item.cracha_label || item.cracha || "-") + "</td>" +
          "<td>" + escapeHtml(item.pessoa || "-") + "</td>" +
          "<td>" + escapeHtml(item.documento || "-") + "</td>" +
          "<td>" + escapeHtml(item.unidade_sigla || "-") + "</td>" +
          "<td>" + escapeHtml(item.entrega || "-") + "</td>" +
          "<td>" + escapeHtml(item.devolucao || "-") + "</td>" +
          '<td><span class="' + badgeClass(item.status) + '">' + escapeHtml(item.status_label || "-") + "</span></td>" +
          '<td class="text-end"><a href="' + escapeHtml(item.view_url || "#") + '" class="btn btn-sm btn-label-info">Ver</a></td>' +
          "</tr>"
        );
      },
    });
  });
})();
