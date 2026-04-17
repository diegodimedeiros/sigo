(function () {
  function requestCatalog(url, queryParam, queryValue) {
    var fullUrl = new URL(url, window.location.origin);
    fullUrl.searchParams.set(queryParam, queryValue);
    // Compatibilidade com versões antigas do endpoint/cliente.
    if (queryParam === "area") {
      fullUrl.searchParams.set("area_atendimento", queryValue);
    }
    var fetchFn = (window.SigoCsrf && typeof window.SigoCsrf.fetch === "function")
      ? window.SigoCsrf.fetch.bind(window.SigoCsrf)
      : window.fetch.bind(window);
    return fetchFn(fullUrl.toString(), {
      headers: {
        "X-Requested-With": "XMLHttpRequest"
      }
    }).then(function (response) {
      if (!response.ok) {
        throw new Error("Falha ao carregar catálogo.");
      }
      return response.json();
    });
  }

  function buildOptions(target, values, placeholder) {
    if (!target) return;
    target.innerHTML = "";

    var firstOption = document.createElement("option");
    firstOption.value = "";
    firstOption.textContent = placeholder || "Selecione";
    target.appendChild(firstOption);

    values.forEach(function (item) {
      var option = document.createElement("option");
      option.value = item.chave;
      option.textContent = item.valor;
      target.appendChild(option);
    });
  }

  function syncLocais(areaField, localField) {
    if (!areaField || !localField) return;

    var locaisUrl = areaField.dataset.locaisUrl;
    var currentLocal = localField.dataset.selectedValue || localField.value;

    function refreshLocais(resetSelection) {
      var area = areaField.value;
      if (!locaisUrl || !area) {
        buildOptions(localField, [], "Selecione a área primeiro");
        return;
      }

      requestCatalog(locaisUrl, "area", area)
        .then(function (payload) {
          if (payload && payload.ok === false) {
            throw new Error("Falha ao carregar catálogo.");
          }
          var data = (payload && payload.data) ? payload.data : (payload || {});
          var locais = data.locais || [];
          buildOptions(localField, locais, "Selecione");

          if (!resetSelection && currentLocal && locais.some(function (item) { return item.chave === currentLocal; })) {
            localField.value = currentLocal;
            return;
          }

          if (localField.dataset.selectedValue && locais.some(function (item) { return item.chave === localField.dataset.selectedValue; })) {
            localField.value = localField.dataset.selectedValue;
            return;
          }

          localField.value = "";
        })
        .catch(function () {
          buildOptions(localField, [], "Selecione a área primeiro");
        });
    }

    areaField.addEventListener("change", function () {
      currentLocal = "";
      refreshLocais(true);
    });

    refreshLocais(false);
  }

  function syncToggleFields() {
    function isActive(source) {
      if (!source) return false;
      if (source.type === "checkbox" || source.type === "radio") {
        return !!source.checked;
      }
      var value = String(source.value || "").trim().toLowerCase();
      return value === "true" || value === "1" || value === "sim" || value === "on";
    }

    document.querySelectorAll(".js-toggle-field").forEach(function (node) {
      var sourceName = node.dataset.toggleSource;
      if (!sourceName) return;

      var source = document.getElementById(sourceName) || document.querySelector('[name="' + sourceName + '"]');
      if (!source) return;

      var active = isActive(source);
      node.style.display = active ? "" : "none";
      node.querySelectorAll("input, select, textarea").forEach(function (field) {
        if (field.type === "checkbox" || field.type === "radio") {
          return;
        }
        field.disabled = !active;
      });
    });
  }

  function isTruthyValue(value) {
    var normalized = String(value || "").trim().toLowerCase();
    return normalized === "true" || normalized === "1" || normalized === "sim" || normalized === "on";
  }

  function initToggleBindings() {
    var toggles = ["doenca_preexistente", "alergia", "plano_saude", "houve_remocao", "possui_acompanhante"];
    toggles.forEach(function (fieldId) {
      var field = document.getElementById(fieldId);
      if (!field) return;
      field.addEventListener("change", syncToggleFields);
    });
    syncToggleFields();
  }

  function syncDestinoRules() {
    var seguiuPasseioField = document.getElementById("seguiu_passeio");
    var houveRemocaoField = document.getElementById("houve_remocao");
    if (!seguiuPasseioField || !houveRemocaoField) {
      return;
    }

    function refresh() {
      var seguiuPasseio = isTruthyValue(seguiuPasseioField.value);
      var podeRemover = !seguiuPasseio;

      houveRemocaoField.disabled = !podeRemover;
      if (!podeRemover) {
        houveRemocaoField.value = "false";
      }

      syncToggleFields();
    }

    seguiuPasseioField.addEventListener("change", refresh);
    houveRemocaoField.addEventListener("change", refresh);
    refresh();
  }

  function syncPrimeirosSocorrosRule() {
    var atendimentoField = document.getElementById("atendimentos");
    var primeirosSocorrosField = document.getElementById("primeiros_socorros");
    if (!atendimentoField || !primeirosSocorrosField) {
      return;
    }

    function removeTempOption() {
      var tempOption = primeirosSocorrosField.querySelector('option[data-system-option="nao_realizado"]');
      if (tempOption) {
        tempOption.remove();
      }
    }

    function ensureTempOption() {
      var tempOption = primeirosSocorrosField.querySelector('option[data-system-option="nao_realizado"]');
      if (tempOption) {
        return tempOption;
      }
      tempOption = document.createElement("option");
      tempOption.value = "nao_realizado";
      tempOption.textContent = "Não realizado";
      tempOption.setAttribute("data-system-option", "nao_realizado");
      primeirosSocorrosField.appendChild(tempOption);
      return tempOption;
    }

    function refresh() {
      var atendimentoRealizado = isTruthyValue(atendimentoField.value);
      if (!atendimentoRealizado) {
        ensureTempOption();
        primeirosSocorrosField.value = "nao_realizado";
      } else {
        if (primeirosSocorrosField.value === "nao_realizado") {
          primeirosSocorrosField.value = "";
        }
        removeTempOption();
      }
      primeirosSocorrosField.disabled = !atendimentoRealizado;
    }

    atendimentoField.addEventListener("change", refresh);
    refresh();
  }

  function syncWitnessBlocks() {
    var testemunhaField = document.getElementById("testemunha");
    var addWrapper = document.getElementById("add_testemunha_wrapper");
    var addButton = document.getElementById("add_testemunha_btn");
    var groupWrapper = document.getElementById("testemunhas_group_wrapper");
    var group = document.getElementById("testemunhas_group");
    var blocks = [
      document.getElementById("testemunha_bloco_0"),
      document.getElementById("testemunha_bloco_1")
    ].filter(Boolean);

    if (!testemunhaField || !blocks.length) {
      return;
    }

    function setVisible(node, visible) {
      if (!node) return;
      node.hidden = !visible;
      node.style.display = visible ? "" : "none";
    }

    function applyBlockState(block, visible) {
      if (!block) return;
      setVisible(block, visible);
      block.querySelectorAll("input, select, textarea").forEach(function (field) {
        field.disabled = !visible;
        if (!visible) {
          field.required = false;
          field.value = "";
        }
      });
    }

    function refresh() {
      var enabled = isTruthyValue(testemunhaField.value);
      setVisible(addWrapper, enabled);
      setVisible(groupWrapper, enabled);
      setVisible(group, enabled);

      if (!enabled) {
        blocks.forEach(function (block, index) {
          applyBlockState(block, index === 0 ? false : false);
        });
        if (addButton) addButton.disabled = true;
        return;
      }

      applyBlockState(blocks[0], true);
      blocks[0].querySelectorAll("input").forEach(function (field) {
        field.required = true;
      });

      var secondVisible = blocks[1] && !blocks[1].hidden;
      if (blocks[1]) {
        applyBlockState(blocks[1], secondVisible);
        if (secondVisible) {
          blocks[1].querySelectorAll("input").forEach(function (field) {
            field.required = true;
          });
        }
      }

      if (addButton) {
        addButton.disabled = false;
        addButton.style.display = blocks[1] && blocks[1].hidden ? "" : "none";
      }

      document.querySelectorAll(".remove_testemunha_btn").forEach(function (button) {
        var targetId = button.getAttribute("data-target");
        var target = targetId ? document.getElementById(targetId) : null;
        button.hidden = !target || target.hidden;
        button.disabled = !target || target.hidden;
      });
    }

    testemunhaField.addEventListener("change", refresh);

    if (addButton) {
      addButton.addEventListener("click", function () {
        if (blocks[1]) {
          blocks[1].hidden = false;
        }
        refresh();
      });
    }

    document.querySelectorAll(".remove_testemunha_btn").forEach(function (button) {
      button.addEventListener("click", function () {
        var targetId = button.getAttribute("data-target");
        var target = targetId ? document.getElementById(targetId) : null;
        if (target) {
          target.hidden = true;
        }
        refresh();
      });
    });

    refresh();
  }

  function initPhotoEvidence() {
    if (!window.SesmtPhotoManager || typeof window.SesmtPhotoManager.dual !== "function") {
      return;
    }
    window.SesmtPhotoManager.dual({
      cameraInputId: "fotos_camera",
      deviceInputId: "fotos_dispositivo",
      cameraStatusId: "fotos_camera_status",
      deviceStatusId: "fotos_dispositivo_status",
      totalStatusId: "quantidade_fotos_atendimento",
      listNodeId: "lista_fotos_atendimento",
      emptyNodeId: "lista_fotos_atendimento_vazia"
    });
  }

  function initGeolocationCapture() {
    if (!window.SesmtGeolocation || typeof window.SesmtGeolocation.initCapture !== "function") {
      return;
    }
    window.SesmtGeolocation.initCapture({
      latitudeId: "geo_latitude",
      longitudeId: "geo_longitude",
      containerId: "geolocalizacao_atendimento",
      emptyNodeId: "geolocalizacao_atendimento_vazia"
    });
  }

  function initSignatureCapture() {
    var signatureInput = document.getElementById("assinatura_atendido");
    var statusNode = document.getElementById("assinatura-status");
    var openButton = document.getElementById("btn-assinatura-modal");
    var modalElement = document.getElementById("atendimentoSignatureModal");
    var canvas = document.getElementById("atendimentoSignatureCanvas");
    var clearButton = document.getElementById("atendimentoSignatureClear");
    var saveButton = document.getElementById("atendimentoSignatureSave");
    if (!signatureInput || !statusNode || !openButton || !modalElement || !canvas || !clearButton || !saveButton) {
      return;
    }

    var modal = window.bootstrap ? new window.bootstrap.Modal(modalElement) : null;
    var ctx = canvas.getContext("2d");
    var drawing = false;
    var hasStroke = false;
    var baseCanvasWidth = 900;
    var baseCanvasHeight = 280;
    var logicalCanvasWidth = baseCanvasWidth;
    var logicalCanvasHeight = baseCanvasHeight;

    function resizeCanvasToDisplay() {
      var rect = canvas.getBoundingClientRect();
      var displayWidth = Math.max(Math.round(rect.width || canvas.parentElement.clientWidth || baseCanvasWidth), 1);
      var displayHeight = baseCanvasHeight;
      var ratio = window.devicePixelRatio || 1;
      logicalCanvasWidth = displayWidth;
      logicalCanvasHeight = displayHeight;
      canvas.style.width = "100%";
      canvas.style.height = displayHeight + "px";
      canvas.width = Math.round(displayWidth * ratio);
      canvas.height = Math.round(displayHeight * ratio);
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    }

    function resetCanvas() {
      resizeCanvasToDisplay();
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, logicalCanvasWidth, logicalCanvasHeight);
      ctx.beginPath();
      ctx.strokeStyle = "#cbd5e1";
      ctx.lineWidth = 1;
      ctx.moveTo(32, logicalCanvasHeight - 32);
      ctx.lineTo(logicalCanvasWidth - 32, logicalCanvasHeight - 32);
      ctx.stroke();
      ctx.strokeStyle = "#111827";
      ctx.lineWidth = 2.4;
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      hasStroke = false;
    }

    function updateStatus() {
      statusNode.textContent = signatureInput.value ? "Assinatura capturada" : "Sem assinatura";
      statusNode.className = signatureInput.value ? "text-success small" : "text-muted small";
    }

    function positionFromEvent(event) {
      var rect = canvas.getBoundingClientRect();
      var source = event.touches ? event.touches[0] : event;
      var scaleX = rect.width ? (logicalCanvasWidth / rect.width) : 1;
      var scaleY = rect.height ? (logicalCanvasHeight / rect.height) : 1;
      return {
        x: (source.clientX - rect.left) * scaleX,
        y: (source.clientY - rect.top) * scaleY
      };
    }

    function startDraw(event) {
      drawing = true;
      var pos = positionFromEvent(event);
      ctx.beginPath();
      ctx.moveTo(pos.x, pos.y);
      event.preventDefault();
    }

    function draw(event) {
      if (!drawing) return;
      var pos = positionFromEvent(event);
      ctx.lineTo(pos.x, pos.y);
      ctx.stroke();
      hasStroke = true;
      event.preventDefault();
    }

    function endDraw() {
      drawing = false;
    }

    openButton.addEventListener("click", function () {
      resetCanvas();
      if (signatureInput.value) {
        var image = new Image();
        image.onload = function () {
          ctx.drawImage(image, 0, 0, logicalCanvasWidth, logicalCanvasHeight);
          hasStroke = true;
        };
        image.src = signatureInput.value;
      }
      if (modal) {
        modal.show();
      }
    });

    clearButton.addEventListener("click", resetCanvas);
    saveButton.addEventListener("click", function () {
      if (!hasStroke) {
        statusNode.textContent = "Faça a assinatura antes de confirmar.";
        statusNode.className = "text-danger small";
        return;
      }
      signatureInput.value = canvas.toDataURL("image/png");
      updateStatus();
      if (modal) {
        modal.hide();
      }
    });

    canvas.addEventListener("mousedown", startDraw);
    canvas.addEventListener("mousemove", draw);
    canvas.addEventListener("mouseup", endDraw);
    canvas.addEventListener("mouseleave", endDraw);
    canvas.addEventListener("touchstart", startDraw, { passive: false });
    canvas.addEventListener("touchmove", draw, { passive: false });
    canvas.addEventListener("touchend", endDraw);
    window.addEventListener("resize", function () {
      if (!modalElement.classList.contains("show")) {
        return;
      }
      resetCanvas();
      if (signatureInput.value) {
        var image = new Image();
        image.onload = function () {
          ctx.drawImage(image, 0, 0, logicalCanvasWidth, logicalCanvasHeight);
          hasStroke = true;
        };
        image.src = signatureInput.value;
      }
    });

    resetCanvas();
    updateStatus();
  }

  function syncContactRegionFields() {
    var tipoPessoaField = document.getElementById("tipo_pessoa");
    var paisField = document.getElementById("contato_pais");
    var estadoField = document.getElementById("contato_estado");
    var provinciaField = document.getElementById("contato_provincia");
    var nacionalidadeField = document.querySelector('[name="pessoa_nacionalidade"]');
    if (!tipoPessoaField || !paisField || !estadoField || !provinciaField || !nacionalidadeField) {
      return;
    }

    var estadoWrapper = estadoField.closest(".col-md-3") || estadoField.parentElement;
    var provinciaWrapper = provinciaField.closest(".col-md-3") || provinciaField.parentElement;

    function refresh() {
      var tipoPessoa = String(tipoPessoaField.value || "").trim().toLowerCase();
      var estrangeiro = tipoPessoa.indexOf("estrangeiro") !== -1;

      if (estadoWrapper) {
        estadoWrapper.style.display = estrangeiro ? "none" : "";
      }
      estadoField.disabled = estrangeiro;

      if (provinciaWrapper) {
        provinciaWrapper.style.display = estrangeiro ? "" : "none";
      }

      provinciaField.disabled = !estrangeiro;

      if (estrangeiro) {
        nacionalidadeField.value = "";
      } else if (!nacionalidadeField.value) {
        nacionalidadeField.value = "Brasileira";
      }

      if (estrangeiro) {
        paisField.value = "";
      } else if (!paisField.value) {
        paisField.value = "Brasil";
      }
    }

    tipoPessoaField.addEventListener("change", refresh);
    refresh();
  }

  function initAtendimentoList() {
    if (!window.SiopAsyncList) {
      return;
    }

    window.SiopAsyncList.initAsyncList({
      formSelector: "#atendimento-list-form",
      tableBodySelector: "#atendimento-list-body",
      metaSelector: "#atendimento-list-meta",
      paginationSelector: "#atendimento-list-pagination",
      dataKey: "registros",
      columnCount: 7,
      emptyMessage: "Nenhum registro encontrado.",
      metaText: function (total) {
        return total + " atendimento" + (total === 1 ? "" : "s") + " encontrado" + (total === 1 ? "" : "s") + ".";
      },
      renderRow: function (item) {
        var escapeHtml = window.SiopAsyncList.escapeHtml;
        return (
          "<tr>" +
          "<td>#" + escapeHtml(item.id) + "</td>" +
          "<td>" + escapeHtml(item.data || "-") + "</td>" +
          "<td>" + escapeHtml(item.pessoa || "-") + "</td>" +
          "<td>" + escapeHtml(item.tipo_ocorrencia || "-") + "</td>" +
          "<td>" + escapeHtml(item.area || "-") + "</td>" +
            '<td><span class="badge badge-' + escapeHtml(item.atendimento_badge || "info") + '">' + escapeHtml(item.atendimento_label || "-") + '</span></td>' +
          '<td class="text-end"><a href="' + escapeHtml(item.view_url || "#") + '" class="btn btn-sm btn-label-info">Ver</a></td>' +
          "</tr>"
        );
      }
    });
  }

  function initAtendimentoForm() {
    var areaField = document.getElementById("area_atendimento");
    var localField = document.getElementById("local");

    if (areaField && localField) {
      syncLocais(areaField, localField);
    }

    initToggleBindings();
    syncContactRegionFields();
    syncDestinoRules();
    syncPrimeirosSocorrosRule();
    syncWitnessBlocks();
    initPhotoEvidence();
    initGeolocationCapture();
    initSignatureCapture();
  }

  document.addEventListener("DOMContentLoaded", function () {
    initAtendimentoForm();
    initAtendimentoList();
  });
})();
