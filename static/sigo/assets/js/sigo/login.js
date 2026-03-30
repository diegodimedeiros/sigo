(function () {
  function initLoginPasswordToggle() {
    var passwordInput = document.getElementById("id_password");
    var toggleButton = document.getElementById("loginPasswordToggle");

    if (!passwordInput || !toggleButton) {
      return;
    }

    toggleButton.addEventListener("click", function () {
      var isHidden = passwordInput.type === "password";
      passwordInput.type = isHidden ? "text" : "password";
      toggleButton.setAttribute("aria-label", isHidden ? "Ocultar senha" : "Mostrar senha");
      toggleButton.setAttribute("aria-pressed", isHidden ? "true" : "false");
      toggleButton.innerHTML = isHidden
        ? '<i class="fas fa-eye-slash" aria-hidden="true"></i>'
        : '<i class="fas fa-eye" aria-hidden="true"></i>';
    });
  }

  document.addEventListener("DOMContentLoaded", initLoginPasswordToggle);
}());
