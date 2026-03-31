(function () {
  var root = document.documentElement;
  var mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
  var savedTheme = localStorage.getItem("sigo-theme");
  var initialTheme = savedTheme || (mediaQuery.matches ? "dark" : "light");

  root.setAttribute("data-sigo-theme", initialTheme);
  root.setAttribute("data-bs-theme", initialTheme);
})();
