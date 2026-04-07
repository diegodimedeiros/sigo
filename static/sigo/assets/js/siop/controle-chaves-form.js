(function () {
  function badgeClass(status) {
    return status === "devolvida" ? "badge badge-success" : "badge badge-warning";
  }

  function initFiltroAreaChave() {
    var areaSelect = document.getElementById("id_area_chave");
    var chaveSelect = document.getElementById("id_chave");
    if (!areaSelect || !chaveSelect) {
      return;
    }

    var options = Array.from(chaveSelect.querySelectorAll("option[data-area]"));

    function aplicarFiltro() {
      var area = areaSelect.value;
      var atualVisivel = false;

      options.forEach(function (option) {
        var visivel = !area || option.dataset.area === area;
        option.hidden = !visivel;
        option.disabled = !visivel;
        if (visivel && option.value === chaveSelect.value) {
          atualVisivel = true;
        }
      });

      if (chaveSelect.value && !atualVisivel) {
        chaveSelect.value = "";
      }
    }

    areaSelect.addEventListener("change", aplicarFiltro);
    aplicarFiltro();
  }

  document.addEventListener("DOMContentLoaded", function () {
    initFiltroAreaChave();

    if (!window.SiopAsyncList) {
      return;
    }

    window.SiopAsyncList.initAsyncList({
      formSelector: "#controle-chaves-list-form",
      tableBodySelector: "#controle-chaves-list-body",
      metaSelector: "#controle-chaves-list-meta",
      paginationSelector: "#controle-chaves-pagination",
      columnCount: 10,
      emptyMessage: "Nenhum controle de chave encontrado para os filtros informados.",
      metaText: function (total) {
        return total + " chave" + (total === 1 ? "" : "s") + " encontrada" + (total === 1 ? "" : "s") + ".";
      },
      renderRow: function (item) {
        var escapeHtml = window.SiopAsyncList.escapeHtml;
        return (
          "<tr>" +
          "<td>#" + item.id + "</td>" +
          "<td>" + escapeHtml(item.numero || "-") + "</td>" +
          "<td>" + escapeHtml(item.chave || "-") + "</td>" +
          "<td>" + escapeHtml(item.area || "-") + "</td>" +
          "<td>" + escapeHtml(item.pessoa || "-") + "</td>" +
          "<td>" + escapeHtml(item.unidade_sigla || "-") + "</td>" +
          "<td>" + escapeHtml(item.retirada || "-") + "</td>" +
          "<td>" + escapeHtml(item.devolucao || "-") + "</td>" +
          '<td><span class="' + badgeClass(item.status) + '">' + escapeHtml(item.status_label || "-") + "</span></td>" +
          '<td class="text-end"><a href="' + escapeHtml(item.view_url || "#") + '" class="btn btn-sm btn-primary">Abrir</a></td>' +
          "</tr>"
        );
      },
    });
  });
})();
