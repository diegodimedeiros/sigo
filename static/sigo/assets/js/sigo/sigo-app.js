(function () {
  var root = document.documentElement;
  var button = document.getElementById("themeToggle");
  var mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

  function applyTheme(theme) {
    root.setAttribute("data-sigo-theme", theme);
    root.setAttribute("data-bs-theme", theme);
    localStorage.setItem("sigo-theme", theme);
  }

  function applySystemTheme(event) {
    if (localStorage.getItem("sigo-theme")) {
      return;
    }

    var systemTheme = event.matches ? "dark" : "light";
    root.setAttribute("data-sigo-theme", systemTheme);
    root.setAttribute("data-bs-theme", systemTheme);
  }

  if (button) {
    button.addEventListener("click", function () {
      var current = root.getAttribute("data-sigo-theme") || "light";
      applyTheme(current === "dark" ? "light" : "dark");
    });
  }

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
