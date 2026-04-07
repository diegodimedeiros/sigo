(function () {
  document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("acesso-terceiros-form");
    if (!form || !window.SiopAsyncForm) {
      return;
    }
    window.SiopAsyncForm.submitAsyncForm(form);
  });
})();
