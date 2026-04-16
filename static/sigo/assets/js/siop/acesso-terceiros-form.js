(function () {
  document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("acesso-terceiros-form");
    if (form && window.SiopAsyncForm) {
      window.SiopAsyncForm.submitAsyncForm(form);
    }

    if (!window.SiopAsyncList) {
      return;
    }

    window.SiopAsyncList.initAsyncList({
      formSelector: "#acesso-terceiros-list-form",
      tableBodySelector: "#acesso-terceiros-list-body",
      metaSelector: "#acesso-terceiros-list-meta",
      paginationSelector: "#acesso-terceiros-list-pagination",
      dataKey: "acessos",
      columnCount: 9,
      emptyMessage: "Nenhum registro encontrado.",
      metaText: function (total) {
        return total + " acesso" + (total === 1 ? "" : "s") + " encontrado" + (total === 1 ? "" : "s") + ".";
      },
      renderRow: function (item) {
        var escapeHtml = window.SiopAsyncList.escapeHtml;
        var statusHtml = item.saida
          ? '<span class="badge badge-success">Finalizada</span>'
          : '<span class="badge badge-warning">Em aberto</span>';
        return (
          "<tr>" +
          "<td>#" + item.id + "</td>" +
          "<td>" + escapeHtml(item.entrada || "-") + "</td>" +
          "<td>" + escapeHtml(item.empresa || "-") + "</td>" +
          "<td>" + escapeHtml(item.nome || "-") + "</td>" +
          "<td>" + escapeHtml(item.documento || "-") + "</td>" +
          "<td>" + escapeHtml(item.p1 || "-") + "</td>" +
          "<td>" + escapeHtml(item.saida || "-") + "</td>" +
          "<td>" + statusHtml + "</td>" +
          '<td class="text-end"><a href="' + escapeHtml(item.view_url || "#") + '" class="btn btn-sm btn-label-info">Ver</a></td>' +
          "</tr>"
        );
      }
    });
  });
})();
