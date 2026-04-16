(function () {
  function initHimenopterosExport() {
    var form = document.getElementById("himenopteros-export-form");
    if (!form) return;
    var apiUrl = form.dataset.apiUrl;
    if (!apiUrl) return;
    window.SesmtExportHandler.bind("himenopteros-export-form", apiUrl, "himenopteros_export.xlsx");
  }

  document.addEventListener("DOMContentLoaded", initHimenopterosExport);
})();
