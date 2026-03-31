(function (window, document) {
  function initSiopDashboardCharts() {
    if (typeof window.Chart === "undefined" || !window.SigoDashboardCharts) {
      return;
    }

    if (!document.getElementById("siopMovimentoChart")) {
      return;
    }

    var charts = window.SigoDashboardCharts;
    var movementData = charts.parseJsonScript("siop-chart-movimento-data", { labels: [], datasets: [] });
    var totalData = charts.parseJsonScript("siop-chart-ocorrencias-total-data", { labels: [], values: [] });
    var achadosStatusData = charts.parseJsonScript("siop-chart-achados-status-data", { labels: [], values: [] });
    var acessosStatusData = charts.parseJsonScript("siop-chart-acessos-status-data", { labels: [], values: [] });

    charts.createLineChart({
      canvasId: "siopMovimentoChart",
      data: movementData,
    });

    charts.createBarChart({
      canvasId: "siopOcorrenciasTotalChart",
      label: "Ocorrências",
      data: totalData,
      seriesColor: "#2563eb",
      borderRadius: 10,
      maxBarThickness: 42,
    });

    charts.createDoughnutChart({
      canvasId: "siopAchadosStatusChart",
      data: achadosStatusData,
      colors: ["#1572e8", "#31ce36", "#ffad46", "#f25961", "#6861ce"],
    });

    charts.createDoughnutChart({
      canvasId: "siopAcessosStatusChart",
      data: acessosStatusData,
      colors: ["#ffad46", "#31ce36"],
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initSiopDashboardCharts);
  } else {
    initSiopDashboardCharts();
  }
})(window, document);
