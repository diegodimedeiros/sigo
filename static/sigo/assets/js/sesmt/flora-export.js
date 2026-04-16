(function () {
  function initFloraExport() {
    var form = document.getElementById("flora-export-form");
    if (!form) return;
    var apiUrl = form.dataset.apiUrl;
    if (!apiUrl) return;
    window.SesmtExportHandler.bind("flora-export-form", apiUrl, "sesmt_flora_export.xlsx");
  }

  document.addEventListener("DOMContentLoaded", initFloraExport);
})();
