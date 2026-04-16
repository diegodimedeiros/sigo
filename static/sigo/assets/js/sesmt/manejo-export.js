(function () {
  function initManejoExport() {
    var form = document.getElementById("manejo-export-form");
    if (!form) return;
    var apiUrl = form.dataset.apiUrl;
    if (!apiUrl) return;
    window.SesmtExportHandler.bind("manejo-export-form", apiUrl, "manejo_export.xlsx");
  }

  document.addEventListener("DOMContentLoaded", initManejoExport);
})();
