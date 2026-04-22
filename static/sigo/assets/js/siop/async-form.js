(function () {
  if (window.SharedAsyncForm || window.SiopAsyncForm) {
    window.SharedAsyncForm = window.SharedAsyncForm || window.SiopAsyncForm;
    window.SiopAsyncForm = window.SharedAsyncForm;
    return;
  }

  if (document.querySelector('script[data-shared-async-form-loader="true"]')) {
    return;
  }

  var script = document.createElement("script");
  script.src = "/static/sigo/assets/js/shared/async-form.js";
  script.async = false;
  script.dataset.sharedAsyncFormLoader = "true";
  document.head.appendChild(script);
})();
