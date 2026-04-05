(function () {
  function getFeedbackBox(form) {
    return form.querySelector(".js-form-feedback");
  }

  function showFormFeedback(form, message, type) {
    var box = getFeedbackBox(form);
    if (!box) return;
    box.className = "alert alert-" + (type || "danger") + " js-form-feedback";
    box.textContent = message;
    box.classList.remove("d-none");
  }

  function hideFormFeedback(form) {
    var box = getFeedbackBox(form);
    if (!box) return;
    box.className = "alert alert-danger d-none js-form-feedback";
    box.textContent = "";
  }

  function clearFieldErrors(form) {
    form.querySelectorAll(".field-error").forEach(function (node) {
      node.textContent = "";
      node.classList.add("d-none");
    });
    form.querySelectorAll(".is-invalid").forEach(function (node) {
      node.classList.remove("is-invalid");
    });
  }

  function resolveErrorTarget(control) {
    if (!control) return null;

    var wrapper = control.parentElement;
    if (!wrapper) return null;

    var existing = wrapper.querySelector(".field-error");
    if (existing) return existing;

    var node = document.createElement("div");
    node.className = "invalid-feedback d-block field-error d-none";
    wrapper.appendChild(node);
    return node;
  }

  function renderFieldErrors(form, details) {
    Object.entries(details || {}).forEach(function (entry) {
      var fieldName = entry[0];
      var messages = entry[1];
      var normalized = Array.isArray(messages) ? messages.join(" ") : String(messages || "");

      if (fieldName === "__all__") {
        showFormFeedback(form, normalized, "danger");
        return;
      }

      var controls = Array.from(form.querySelectorAll('[name="' + fieldName + '"]'));
      if (!controls.length) {
        return;
      }

      controls.forEach(function (control) {
        control.classList.add("is-invalid");
      });

      var target = form.querySelector('[data-field-error="' + fieldName + '"]') || resolveErrorTarget(controls[0]);
      if (!target) return;
      target.textContent = normalized;
      target.classList.remove("d-none");
    });
  }

  function submitAsyncForm(form) {
    if (!form || typeof window.SigoCsrf === "undefined") {
      return;
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      hideFormFeedback(form);
      clearFieldErrors(form);

      var submitButton = form.querySelector('[type="submit"]');
      var originalLabel = submitButton ? submitButton.textContent : "";
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "Salvando...";
      }

      window.SigoCsrf.fetch(form.action || window.location.pathname, {
        method: "POST",
        body: new FormData(form),
      })
        .then(function (response) {
          return response.json().then(function (payload) {
            return { response: response, payload: payload };
          });
        })
        .then(function (result) {
          var payload = result.payload || {};
          if (result.response.ok && payload.ok) {
            var redirectUrl = ((payload.data || {}).redirect_url) || ((payload.data || {}).view_url);
            if (redirectUrl) {
              window.location.href = redirectUrl;
              return;
            }
            showFormFeedback(form, payload.message || "Registro salvo com sucesso.", "success");
            return;
          }

          var error = payload.error || {};
          renderFieldErrors(form, error.details || {});
          showFormFeedback(form, error.message || "Não foi possível salvar o formulário.", "danger");
        })
        .catch(function () {
          showFormFeedback(form, "Erro ao enviar o formulário. Tente novamente.", "danger");
        })
        .finally(function () {
          if (submitButton) {
            submitButton.disabled = false;
            submitButton.textContent = originalLabel;
          }
        });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll('form[data-async-form="true"]').forEach(function (form) {
      submitAsyncForm(form);
    });
  });
})();
