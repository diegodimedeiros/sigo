(function () {
  var savedTheme = localStorage.getItem("sigo-theme") || "light";
  document.documentElement.setAttribute("data-sigo-theme", savedTheme);
})();
