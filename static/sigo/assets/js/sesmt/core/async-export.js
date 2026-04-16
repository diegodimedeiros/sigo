/**
 * SESMT Export Handler - Reusable async export logic
 * Handles form submission, file download, button state, and error handling
 */
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

  function getFilenameFromResponse(response, fallback) {
    var disposition = response.headers.get("Content-Disposition") || "";
    var match = disposition.match(/filename="?([^"]+)"?/i);
    return match && match[1] ? match[1] : fallback;
  }

  function resolveSubmitButton(form) {
    if (!form) return null;
    return form.querySelector('[type="submit"]') || document.querySelector('[form="' + form.id + '"]');
  }

  /**
   * Binds export functionality to a form
   * @param {string} formId - The ID of the export form
   * @param {string} apiUrl - The API endpoint for export
   * @param {string} fallbackFilename - Default filename if not provided by server
   */
  window.SesmtExportHandler = {
    bind: function (formId, apiUrl, fallbackFilename) {
      if (!formId || !apiUrl) {
        return;
      }

      var form = document.getElementById(formId);
      if (!form) {
        return;
      }

      form.addEventListener("submit", function (event) {
        event.preventDefault();

        var submitButton = resolveSubmitButton(form);
        var originalText = submitButton ? submitButton.textContent : "";

        if (submitButton) {
          submitButton.disabled = true;
          if (originalText.trim()) {
            submitButton.textContent = "Gerando...";
          }
        }

        window
          .fetch(apiUrl, {
            method: "POST",
            body: new FormData(form),
            headers: {
              "X-Requested-With": "XMLHttpRequest"
            }
          })
          .then(function (response) {
            if (!response.ok) {
              throw new Error("Falha ao exportar.");
            }
            return response.blob().then(function (blob) {
              return { response: response, blob: blob };
            });
          })
          .then(function (result) {
            var filename = getFilenameFromResponse(result.response, fallbackFilename || "export.xlsx");
            downloadBlob(result.blob, filename);
          })
          .catch(function () {
            window.alert("Não foi possível gerar a exportação.");
          })
          .finally(function () {
            if (submitButton) {
              submitButton.disabled = false;
              if (originalText.trim()) {
                submitButton.textContent = originalText;
              }
            }
          });
      });
    }
  };
})();
