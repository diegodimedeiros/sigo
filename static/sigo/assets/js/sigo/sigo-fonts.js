(function () {
  if (typeof WebFont === "undefined") {
    return;
  }

  var staticPrefix = document.documentElement.dataset.staticPrefix || "/static/";
  if (!staticPrefix.endsWith("/")) {
    staticPrefix += "/";
  }

  WebFont.load({
    custom: {
      families: [
        "Font Awesome 5 Solid",
        "Font Awesome 5 Regular",
        "Font Awesome 5 Brands",
        "simple-line-icons",
      ],
      urls: [staticPrefix + "sigo/assets/css/fonts.min.css"],
    },
    active: function () {
      sessionStorage.fonts = true;
    },
  });
})();
