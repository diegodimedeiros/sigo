(function (window, document) {
  function parseJsonScript(scriptId, fallbackValue) {
    var script = document.getElementById(scriptId);

    if (!script) {
      return fallbackValue;
    }

    try {
      return JSON.parse(script.textContent);
    } catch (error) {
      console.warn("Nao foi possivel ler os dados do grafico:", scriptId, error);
      return fallbackValue;
    }
  }

  function getThemeColors() {
    var isDark = document.documentElement.getAttribute("data-sigo-theme") === "dark";

    return {
      isDark: isDark,
      textColor: isDark ? "#dbe5f4" : "#334155",
      mutedColor: isDark ? "#94a3b8" : "#64748b",
      gridColor: isDark ? "rgba(148, 163, 184, 0.18)" : "rgba(148, 163, 184, 0.2)",
    };
  }

  function createChart(canvasId, config) {
    var canvas = document.getElementById(canvasId);

    if (!canvas || typeof window.Chart === "undefined") {
      return null;
    }

    return new window.Chart(canvas, config);
  }

  function createLineChart(options) {
    var data = options.data || {};
    var labels = data.labels || [];
    var datasets = data.datasets || [];
    var theme = getThemeColors();

    if (!labels.length || !datasets.length) {
      return null;
    }

    return createChart(options.canvasId, {
      type: "line",
      data: {
        labels: labels,
        datasets: datasets.map(function (dataset) {
          return {
            label: dataset.label,
            data: dataset.data || [],
            borderColor: dataset.borderColor,
            backgroundColor: dataset.backgroundColor,
            fill: false,
            tension: options.tension || 0.35,
            borderWidth: options.borderWidth || 2.5,
            pointRadius: options.pointRadius || 4,
            pointHoverRadius: options.pointHoverRadius || 5,
          };
        }),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: theme.textColor,
              usePointStyle: true,
              boxWidth: 10,
            },
          },
        },
        scales: {
          x: {
            ticks: { color: theme.mutedColor },
            grid: { color: theme.gridColor },
          },
          y: {
            beginAtZero: true,
            ticks: {
              color: theme.mutedColor,
              precision: 0,
              stepSize: 1,
              callback: function (value) {
                return Number.isInteger(value) ? value : "";
              },
            },
            grid: { color: theme.gridColor },
          },
        },
      },
    });
  }

  function createBarChart(options) {
    var data = options.data || {};
    var labels = data.labels || [];
    var values = data.values || [];
    var theme = getThemeColors();

    if (!labels.length || !values.length) {
      return null;
    }

    return createChart(options.canvasId, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{
          label: options.label || "Total",
          data: values,
          backgroundColor: options.seriesColor || "#2563eb",
          borderRadius: options.borderRadius || 10,
          borderSkipped: false,
          maxBarThickness: options.maxBarThickness || 42,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: theme.textColor,
              usePointStyle: true,
              boxWidth: 10,
            },
          },
        },
        scales: {
          x: {
            ticks: { color: theme.mutedColor },
            grid: { display: false },
          },
          y: {
            beginAtZero: true,
            ticks: {
              color: theme.mutedColor,
              precision: 0,
              stepSize: 1,
              callback: function (value) {
                return Number.isInteger(value) ? value : "";
              },
            },
            grid: { color: theme.gridColor },
          },
        },
      },
    });
  }

  function createDoughnutChart(options) {
    var data = options.data || {};
    var labels = data.labels || [];
    var values = data.values || [];
    var theme = getThemeColors();

    if (!labels.length || !values.length) {
      return null;
    }

    return createChart(options.canvasId, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [{
          data: values,
          backgroundColor: options.colors || ["#1572e8", "#31ce36", "#ffad46"],
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: options.cutout || "64%",
        plugins: {
          legend: {
            position: options.legendPosition || "bottom",
            labels: {
              color: theme.textColor,
              usePointStyle: true,
              boxWidth: 9,
              padding: 14,
            },
          },
        },
      },
    });
  }

  window.SigoDashboardCharts = {
    parseJsonScript: parseJsonScript,
    getThemeColors: getThemeColors,
    createLineChart: createLineChart,
    createBarChart: createBarChart,
    createDoughnutChart: createDoughnutChart,
  };
})(window, document);
