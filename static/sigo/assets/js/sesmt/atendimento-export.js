(function () {
  function initAtendimentoExport() {
    var form = document.getElementById("atendimento-export-form");
    if (!form) return;
    var apiUrl = form.dataset.apiUrl;
    if (!apiUrl) return;
    window.SesmtExportHandler.bind("atendimento-export-form", apiUrl, "atendimento_export.xlsx");
  }

  document.addEventListener("DOMContentLoaded", initAtendimentoExport);
})();
