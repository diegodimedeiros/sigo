(function () {
  var root = document.documentElement;
  var mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
  var savedTheme = localStorage.getItem("sigo-theme");
  var supportedThemes = ["light", "dark", "forest", "aqua"];

  function normalizeTheme(theme) {
    if (supportedThemes.indexOf(theme) !== -1) {
      return theme;
    }
    // Sempre iniciar com light se não houver tema salvo
    return "light";
  }

  function toBootstrapTheme(theme) {
    return theme === "dark" ? "dark" : "light";
  }

  var initialTheme = normalizeTheme(savedTheme);

  root.setAttribute("data-sigo-theme", initialTheme);
  root.setAttribute("data-bs-theme", toBootstrapTheme(initialTheme));
})();
