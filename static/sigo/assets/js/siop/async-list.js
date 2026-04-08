(function () {
  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function buildQueryString(form, page, pageSize) {
    var params = new URLSearchParams(new FormData(form));
    if (page && page > 1) {
      params.set("page", String(page));
    } else {
      params.delete("page");
    }
    params.set("limit", String(pageSize));
    params.set("offset", String(Math.max(0, (page - 1) * pageSize)));
    return params.toString();
  }

  function buildPageUrl(form, page) {
    var params = new URLSearchParams(new FormData(form));
    if (page && page > 1) {
      params.set("page", String(page));
    } else {
      params.delete("page");
    }
    var query = params.toString();
    return window.location.pathname + (query ? "?" + query : "");
  }

  function buildPagination(total, pageSize, page) {
    var totalPages = Math.max(1, Math.ceil(total / pageSize));
    var hasPrevious = page > 1;
    var hasNext = page < totalPages;

    function renderControl(label, targetPage, disabled) {
      if (disabled) {
        return '<li class="page-item disabled"><span class="page-link">' + label + "</span></li>";
      }
      return (
        '<li class="page-item"><a class="page-link" href="#" data-page="' +
        targetPage +
        '">' +
        label +
        "</a></li>"
      );
    }

    return (
      '<div class="card-footer d-flex justify-content-between align-items-center flex-wrap gap-3">' +
      '<span class="text-muted small">Página ' +
      page +
      " de " +
      totalPages +
      " · Total encontrado: " +
      total +
      " registro" +
      (total === 1 ? "" : "s") +
      "</span>" +
      '<ul class="pagination pg-primary mb-0">' +
      renderControl("Primeira", 1, !hasPrevious) +
      renderControl("Anterior", page - 1, !hasPrevious) +
      '<li class="page-item active"><span class="page-link">' +
      page +
      "</span></li>" +
      renderControl("Próxima", page + 1, !hasNext) +
      renderControl("Última", totalPages, !hasNext) +
      "</ul></div>"
    );
  }

  function buildSingleFooter(total) {
    return (
      '<div class="card-footer d-flex justify-content-between align-items-center">' +
      '<span class="text-muted small">Total encontrado: ' +
      total +
      " registro" +
      (total === 1 ? "" : "s") +
      "</span></div>"
    );
  }

  function initAsyncList(config) {
    if (!config) {
      return;
    }

    var form = document.querySelector(config.formSelector);
    var tableBody = document.querySelector(config.tableBodySelector);
    var meta = document.querySelector(config.metaSelector);
    var pagination = document.querySelector(config.paginationSelector);
    if (!form || !tableBody || !meta || !pagination) {
      return;
    }

    var apiUrl = form.dataset.apiUrl || config.apiUrl;
    var dataKey = config.dataKey || "registros";
    var pageSize = Number(form.dataset.pageSize || config.pageSize || 20);
    var currentPage = Number(new URLSearchParams(window.location.search).get("page") || "1");
    var loadingText = config.loadingText || "Carregando registros...";
    var emptyMessage = config.emptyMessage || "Nenhum registro encontrado.";

    function setLoadingState() {
      tableBody.innerHTML =
        '<tr><td colspan="' +
        config.columnCount +
        '" class="text-center py-4 text-muted">' +
        escapeHtml(loadingText) +
        "</td></tr>";
    }

    function renderRows(registros) {
      if (!registros.length) {
        tableBody.innerHTML =
          '<tr><td colspan="' +
          config.columnCount +
          '" class="text-center py-4 text-muted">' +
          escapeHtml(emptyMessage) +
          "</td></tr>";
        return;
      }
      tableBody.innerHTML = registros.map(config.renderRow).join("");
    }

    function renderMeta(total) {
      meta.textContent = config.metaText(total);
    }

    function renderPagination(total) {
      if (total > pageSize) {
        pagination.innerHTML = buildPagination(total, pageSize, currentPage);
        return;
      }
      pagination.innerHTML = buildSingleFooter(total);
    }

    function fetchPage(pushState) {
      setLoadingState();
      var query = buildQueryString(form, currentPage, pageSize);
      var requestUrl = apiUrl + (query ? "?" + query : "");
      window
        .fetch(requestUrl, {
          headers: {
            "X-Requested-With": "XMLHttpRequest",
          },
        })
        .then(function (response) {
          return response.json().then(function (payload) {
            return { response: response, payload: payload };
          });
        })
        .then(function (result) {
          if (!result.response.ok || !result.payload.ok) {
            throw new Error("Falha ao carregar listagem.");
          }
          var data = (result.payload.data || {})[dataKey] || [];
          var paginationMeta = ((result.payload.meta || {}).pagination) || {};
          var total = Number(paginationMeta.total || data.length || 0);
          renderRows(data);
          renderMeta(total);
          renderPagination(total);
          if (pushState !== false) {
            window.history.replaceState({}, "", buildPageUrl(form, currentPage));
          }
        })
        .catch(function () {
          tableBody.innerHTML =
            '<tr><td colspan="' +
            config.columnCount +
            '" class="text-center py-4 text-muted">Não foi possível carregar a listagem.</td></tr>';
        });
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      currentPage = 1;
      fetchPage(true);
    });

    form.addEventListener("reset", function () {
      window.setTimeout(function () {
        currentPage = 1;
        fetchPage(true);
      }, 0);
    });

    form.addEventListener("click", function (event) {
      var resetLink = event.target.closest("[data-reset-filters]");
      if (!resetLink) {
        return;
      }
      event.preventDefault();
      form.reset();
      currentPage = 1;
      fetchPage(true);
    });

    pagination.addEventListener("click", function (event) {
      var pageLink = event.target.closest("[data-page]");
      if (!pageLink) {
        return;
      }
      event.preventDefault();
      currentPage = Number(pageLink.dataset.page || "1");
      fetchPage(true);
    });

    form.addEventListener("click", function (event) {
      var sortLink = event.target.closest("[data-sort-field]");
      if (!sortLink) {
        return;
      }
      event.preventDefault();
      var sortFieldInput = form.querySelector('[name="sort"]');
      var sortDirInput = form.querySelector('[name="dir"]');
      if (!sortFieldInput || !sortDirInput) {
        return;
      }
      sortFieldInput.value = sortLink.dataset.sortField || "";
      sortDirInput.value = sortLink.dataset.sortDir || "asc";
      currentPage = 1;
      fetchPage(true);
    });

    fetchPage(false);
  }

  window.SiopAsyncList = {
    escapeHtml: escapeHtml,
    initAsyncList: initAsyncList,
  };
})();
