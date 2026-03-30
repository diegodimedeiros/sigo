(function () {
  var root = document.documentElement;
  var button = document.getElementById("themeToggle");

  function applyTheme(theme) {
    root.setAttribute("data-sigo-theme", theme);
    localStorage.setItem("sigo-theme", theme);
  }

  if (button) {
    button.addEventListener("click", function () {
      var current = root.getAttribute("data-sigo-theme") || "light";
      applyTheme(current === "dark" ? "light" : "dark");
    });
  }
})();
