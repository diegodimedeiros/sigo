(function () {
  function downloadBlob(blob, filename) {
    var url = window.URL.createObjectURL(blob);
    var link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  }

  function getFilename(response, fallback) {
    var disposition = response.headers.get("Content-Disposition") || "";
    var match = disposition.match(/filename="?([^"]+)"?/i);
    return match && match[1] ? match[1] : fallback;
  }

  function initFloraExport() {
    var form = document.getElementById("flora-export-form");
    if (!form || typeof window.SigoCsrf === "undefined") return;
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var submit = form.querySelector('[type="submit"]');
      var original = submit ? submit.textContent : "";
      if (submit) {
        submit.disabled = true;
        submit.textContent = "Gerando...";
      }
      window.SigoCsrf.fetch(form.dataset.apiUrl, { method: "POST", body: new FormData(form) })
        .then(function (response) {
          if (!response.ok) throw new Error("Falha ao exportar.");
          return response.blob().then(function (blob) {
            return { response: response, blob: blob };
          });
        })
        .then(function (result) {
          downloadBlob(result.blob, getFilename(result.response, "sesmt_flora_export.xlsx"));
        })
        .catch(function () {
          window.alert("Não foi possível gerar a exportação.");
        })
        .finally(function () {
          if (submit) {
            submit.disabled = false;
            submit.textContent = original;
          }
        });
    });
  }

  document.addEventListener("DOMContentLoaded", initFloraExport);
})();
