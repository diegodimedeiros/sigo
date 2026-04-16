(function () {
  function badgeClass(status) {
    return status === "devolvido" ? "badge badge-success" : "badge badge-warning";
  }

  function initFiltroTipoAtivo() {
    var tipoSelect = document.getElementById("id_tipo_ativo");
    var ativoSelect = document.getElementById("id_equipamento");
    if (!tipoSelect || !ativoSelect) {
      return;
    }

    var grupos = Array.from(ativoSelect.querySelectorAll("optgroup"));
    var placeholder = ativoSelect.querySelector('option[value=""]');

    function aplicarFiltro() {
      var tipoSelecionado = tipoSelect.value;
      var ativoAtualAindaVisivel = false;

      grupos.forEach(function (grupo) {
        var visivel = !tipoSelecionado || grupo.dataset.grupo === tipoSelecionado;
        grupo.disabled = !visivel;
        grupo.hidden = !visivel;
        if (visivel && grupo.querySelector('option[value="' + ativoSelect.value + '"]')) {
          ativoAtualAindaVisivel = true;
        }
      });

      if (placeholder) {
        placeholder.hidden = false;
      }

      if (ativoSelect.value && !ativoAtualAindaVisivel) {
        ativoSelect.value = "";
      }
    }

    tipoSelect.addEventListener("change", aplicarFiltro);
    aplicarFiltro();
  }

  document.addEventListener("DOMContentLoaded", function () {
    initFiltroTipoAtivo();

    if (!window.SiopAsyncList) {
      return;
    }

    window.SiopAsyncList.initAsyncList({
      formSelector: "#controle-ativos-list-form",
      tableBodySelector: "#controle-ativos-list-body",
      metaSelector: "#controle-ativos-list-meta",
      paginationSelector: "#controle-ativos-pagination",
      columnCount: 9,
      emptyMessage: "Nenhum registro encontrado.",
      metaText: function (total) {
        return total + " ativo" + (total === 1 ? "" : "s") + " encontrado" + (total === 1 ? "" : "s") + ".";
      },
      renderRow: function (item) {
        var escapeHtml = window.SiopAsyncList.escapeHtml;
        return (
          "<tr>" +
          "<td>#" + item.id + "</td>" +
          "<td>" + escapeHtml(item.equipamento_label || item.equipamento || "-") + "</td>" +
          "<td>" + escapeHtml(item.pessoa || "-") + "</td>" +
          "<td>" + escapeHtml(item.destino_label || item.destino || "-") + "</td>" +
          "<td>" + escapeHtml(item.unidade_sigla || "-") + "</td>" +
          "<td>" + escapeHtml(item.retirada || "-") + "</td>" +
          "<td>" + escapeHtml(item.devolucao || "-") + "</td>" +
          '<td><span class="' + badgeClass(item.status) + '">' + escapeHtml(item.status_label || "-") + "</span></td>" +
          '<td class="text-end"><a href="' + escapeHtml(item.view_url || "#") + '" class="btn btn-sm btn-label-info">Ver</a></td>' +
          "</tr>"
        );
      },
    });
  });
})();
