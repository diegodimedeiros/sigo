(function () {
  var root = document.documentElement;
  var button = document.getElementById("themeToggle");
  var themeOptions = document.querySelectorAll("[data-theme-option]");
  var mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
  var supportedThemes = ["light", "dark", "forest", "aqua"];

  function normalizeTheme(theme) {
    if (supportedThemes.indexOf(theme) !== -1) {
      return theme;
    }
    return mediaQuery.matches ? "dark" : "light";
  }

  function toBootstrapTheme(theme) {
    return theme === "dark" ? "dark" : "light";
  }

  function updateThemeUi(theme) {
    if (button) {
      button.setAttribute("data-theme-current", theme);
      button.setAttribute("title", "Tema: " + theme);
      button.setAttribute("aria-label", "Tema atual: " + theme);
    }

    if (!themeOptions.length) {
      return;
    }

    themeOptions.forEach(function (option) {
      var optionTheme = option.getAttribute("data-theme-option");
      var isActive = optionTheme === theme;
      option.classList.toggle("active", isActive);
      option.setAttribute("aria-current", isActive ? "true" : "false");
    });
  }

  function applyTheme(theme) {
    var normalized = normalizeTheme(theme);
    root.setAttribute("data-sigo-theme", normalized);
    root.setAttribute("data-bs-theme", toBootstrapTheme(normalized));
    localStorage.setItem("sigo-theme", normalized);
    updateThemeUi(normalized);
  }

  function applySystemTheme(event) {
    if (localStorage.getItem("sigo-theme")) {
      return;
    }

    var systemTheme = event.matches ? "dark" : "light";
    root.setAttribute("data-sigo-theme", systemTheme);
    root.setAttribute("data-bs-theme", toBootstrapTheme(systemTheme));
    updateThemeUi(systemTheme);
  }

  if (themeOptions.length) {
    themeOptions.forEach(function (option) {
      option.addEventListener("click", function (event) {
        event.preventDefault();
        var selectedTheme = option.getAttribute("data-theme-option");
        applyTheme(selectedTheme);
      });
    });
  } else if (button) {
    button.addEventListener("click", function () {
      var current = normalizeTheme(root.getAttribute("data-sigo-theme") || "light");
      var currentIndex = supportedThemes.indexOf(current);
      var nextTheme = supportedThemes[(currentIndex + 1) % supportedThemes.length];
      applyTheme(nextTheme);
    });
  }

  updateThemeUi(normalizeTheme(root.getAttribute("data-sigo-theme") || "light"));

  if (typeof mediaQuery.addEventListener === "function") {
    mediaQuery.addEventListener("change", applySystemTheme);
  } else if (typeof mediaQuery.addListener === "function") {
    mediaQuery.addListener(applySystemTheme);
  }
})();

(function () {
  function bindSidebarHoverBehavior() {
    var wrapper = document.querySelector(".wrapper");
    var sidebar = document.querySelector(".sidebar");

    if (!wrapper || !sidebar) {
      return;
    }

    function isDesktop() {
      return window.innerWidth >= 992;
    }

    function isMinimized() {
      return wrapper.classList.contains("sidebar_minimize");
    }

    function openHover() {
      if (!isDesktop() || !isMinimized()) {
        return;
      }

      wrapper.classList.add("sidebar_minimize_hover");
    }

    function closeHover() {
      wrapper.classList.remove("sidebar_minimize_hover");
    }

    sidebar.addEventListener("mouseenter", openHover);
    sidebar.addEventListener("mouseleave", closeHover);

    sidebar.querySelectorAll(".nav-item > a").forEach(function (link) {
      link.addEventListener("click", function () {
        if (isMinimized()) {
          closeHover();
        }
      });
    });

    window.addEventListener("resize", function () {
      if (!isDesktop()) {
        closeHover();
      }
    });

    document.querySelectorAll(".toggle-sidebar").forEach(function (toggle) {
      toggle.addEventListener("click", function () {
        window.setTimeout(function () {
          if (!isMinimized()) {
            closeHover();
          }
        }, 0);
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindSidebarHoverBehavior);
  } else {
    bindSidebarHoverBehavior();
  }
})();

(function () {
  function animateCounter(element) {
    var target = parseInt(element.getAttribute("data-counter-value"), 10);

    if (Number.isNaN(target)) {
      return;
    }

    if (target <= 0) {
      element.textContent = "0";
      return;
    }

    var duration = 1400;
    var startTime = null;

    function step(timestamp) {
      if (!startTime) {
        startTime = timestamp;
      }

      var progress = Math.min((timestamp - startTime) / duration, 1);
      var eased = 1 - Math.pow(1 - progress, 3);
      var current = Math.round(target * eased);

      element.textContent = String(current);

      if (progress < 1) {
        window.requestAnimationFrame(step);
      } else {
        element.textContent = String(target);
      }
    }

    window.requestAnimationFrame(step);
  }

  function bindCounters() {
    var counters = document.querySelectorAll("[data-counter-value]");

    if (!counters.length) {
      return;
    }

    if (!("IntersectionObserver" in window)) {
      counters.forEach(animateCounter);
      return;
    }

    var observer = new IntersectionObserver(
      function (entries, currentObserver) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) {
            return;
          }

          animateCounter(entry.target);
          currentObserver.unobserve(entry.target);
        });
      },
      {
        threshold: 0.45,
      }
    );

    counters.forEach(function (counter) {
      observer.observe(counter);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindCounters);
  } else {
    bindCounters();
  }
})();
