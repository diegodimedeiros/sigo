(function () {
  function resolveRequestTarget(form, options) {
    var method =
      (options && options.method) ||
      form.dataset.apiMethod ||
      form.getAttribute("method") ||
      "POST";
    var url =
      (options && options.url) ||
      form.dataset.apiUrl ||
      form.getAttribute("action") ||
      window.location.pathname;
    return {
      method: String(method || "POST").toUpperCase(),
      url: url,
    };
  }

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
    form.querySelectorAll(".field-invalid-surface").forEach(function (node) {
      node.classList.remove("field-invalid-surface");
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
        var invalidTargetSelector = control.dataset.invalidTarget;
        if (invalidTargetSelector) {
          var invalidTarget = form.querySelector(invalidTargetSelector);
          if (invalidTarget) {
            invalidTarget.classList.add("field-invalid-surface");
          }
        }
      });

      var target = form.querySelector('[data-field-error="' + fieldName + '"]') || resolveErrorTarget(controls[0]);
      if (!target) return;
      target.textContent = normalized;
      target.classList.remove("d-none");
    });
  }

  function clearControlError(control) {
    if (!control) return;

    control.classList.remove("is-invalid");

    var invalidTargetSelector = control.dataset.invalidTarget;
    if (invalidTargetSelector) {
      var invalidTarget = control.form ? control.form.querySelector(invalidTargetSelector) : null;
      if (invalidTarget) {
        invalidTarget.classList.remove("field-invalid-surface");
      }
    }

    var errorNode = null;
    var namedErrorNode = control.form
      ? control.form.querySelector('[data-field-error="' + control.name + '"]')
      : null;
    if (namedErrorNode) {
      errorNode = namedErrorNode;
    } else {
      var wrapper = control.parentElement;
      if (wrapper) {
        var candidate = wrapper.querySelector(".field-error");
        if (candidate) {
          errorNode = candidate;
        }
      }
    }

    if (errorNode) {
      errorNode.textContent = "";
      errorNode.classList.add("d-none");
    }
  }

  function renderBrowserValidationErrors(form) {
    var invalidControls = Array.from(
      form.querySelectorAll("input, select, textarea")
    ).filter(function (control) {
      return !control.disabled && typeof control.checkValidity === "function" && !control.checkValidity();
    });

    if (!invalidControls.length) {
      return false;
    }

    invalidControls.forEach(function (control) {
      control.classList.add("is-invalid");

      var invalidTargetSelector = control.dataset.invalidTarget;
      if (invalidTargetSelector) {
        var invalidTarget = form.querySelector(invalidTargetSelector);
        if (invalidTarget) {
          invalidTarget.classList.add("field-invalid-surface");
        }
      }

      var target = form.querySelector('[data-field-error="' + control.name + '"]') || resolveErrorTarget(control);
      if (target) {
        target.textContent = control.validationMessage || "Campo obrigatório.";
        target.classList.remove("d-none");
      }
    });

    var firstInvalid = invalidControls[0];
    if (firstInvalid && typeof firstInvalid.focus === "function") {
      firstInvalid.focus();
    }

    showFormFeedback(form, "Preencha todos os campos obrigatórios destacados.", "danger");
    return true;
  }

  function submitAsyncForm(form, options) {
    if (!form || typeof window.SigoCsrf === "undefined") {
      return;
    }

    if (form.dataset.asyncFormBound === "true") {
      return;
    }
    form.dataset.asyncFormBound = "true";

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      hideFormFeedback(form);
      clearFieldErrors(form);

      if (renderBrowserValidationErrors(form)) {
        return;
      }

      if (form.querySelectorAll(".is-invalid").length > 0) {
        showFormFeedback(form, "Preencha todos os campos obrigatórios destacados.", "danger");
        return;
      }

      var requestTarget = resolveRequestTarget(form, options);

      var submitButton = form.querySelector('[type="submit"]');
      var originalLabel = submitButton ? submitButton.textContent : "";
      var queuedForSync = false;

      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "Salvando...";
      }

      window.SigoCsrf.fetch(requestTarget.url, {
        method: requestTarget.method,
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
        .catch(function (err) {
          var isNetworkError = !navigator.onLine ||
            (err && (err.name === "TypeError" || (err.message && err.message.toLowerCase().indexOf("network") !== -1)));
          if (isNetworkError) {
            if (form.querySelectorAll(".is-invalid").length > 0) {
              showFormFeedback(form, "Preencha todos os campos obrigatórios destacados.", "danger");
              if (submitButton) {
                submitButton.disabled = false;
                submitButton.textContent = originalLabel;
              }
              return;
            }
            queuedForSync = true;
            try {
              if (window.location.pathname.indexOf("/reportos/") === 0) {
                window.localStorage.setItem("reportos_pwa_last_queue_at", String(Date.now()));
              }
            } catch (_error) {
              // noop
            }
            if (typeof window.dispatchEvent === "function" && typeof window.CustomEvent === "function") {
              window.dispatchEvent(new CustomEvent("reportos:sync-queued"));
            }
            if (submitButton) {
              submitButton.disabled = true;
              submitButton.textContent = "Aguardando conexão...";
            }
            showFormFeedback(
              form,
              "Sem conexão. Registro enfileirado — será enviado automaticamente ao reconectar.",
              "info"
            );
            var offlineRedirect =
              form.dataset.offlineRedirect ||
              window.location.pathname.split("/").slice(0, -2).join("/") + "/";
            setTimeout(function () {
              window.location.href = offlineRedirect;
            }, 2000);
          } else {
            showFormFeedback(form, "Erro ao enviar o formulário. Tente novamente.", "danger");
          }
        })
        .finally(function () {
          if (submitButton && !queuedForSync) {
            submitButton.disabled = false;
            submitButton.textContent = originalLabel;
          }
        });
    });

    form.querySelectorAll("input, select, textarea").forEach(function (control) {
      var clearIfValid = function () {
        if (!control.classList.contains("is-invalid")) {
          return;
        }
        if (typeof control.checkValidity === "function" && control.checkValidity()) {
          clearControlError(control);
        }
      };

      control.addEventListener("input", clearIfValid);
      control.addEventListener("change", clearIfValid);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll('form[data-async-form="true"]').forEach(function (form) {
      submitAsyncForm(form);
    });
  });

  window.SharedAsyncForm = {
    submitAsyncForm: submitAsyncForm,
  };
  window.SiopAsyncForm = window.SharedAsyncForm;
})();
