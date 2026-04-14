(function () {
  function initHimenopterosExport() {
    var form = document.getElementById("himenopteros-export-form");
    if (!form) return;
    var apiUrl = form.dataset.apiUrl;
    if (!apiUrl) return;

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var formData = new FormData(form);
      window.fetch(apiUrl, {
        method: "POST",
        body: formData,
        headers: { "X-Requested-With": "XMLHttpRequest" }
      })
        .then(function (response) {
          if (!response.ok) throw new Error("Falha ao exportar.");
          return Promise.all([response.blob(), response.headers.get("Content-Disposition")]);
        })
        .then(function (result) {
          var blob = result[0];
          var disposition = result[1] || "";
          var match = disposition.match(/filename=\"?([^\";]+)\"?/i);
          var filename = match ? match[1] : "himenopteros_export.xlsx";
          var url = window.URL.createObjectURL(blob);
          var link = document.createElement("a");
          link.href = url;
          link.download = filename;
          document.body.appendChild(link);
          link.click();
          link.remove();
          window.URL.revokeObjectURL(url);
        })
        .catch(function () {
          window.alert("Não foi possível gerar a exportação.");
        });
    });
  }

  document.addEventListener("DOMContentLoaded", initHimenopterosExport);
})();
