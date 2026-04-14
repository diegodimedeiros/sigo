(function () {
  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function boolLabel(value) {
    return value ? "Sim" : "Não";
  }

  function field(label, value, colClass) {
    return '<div class="' + (colClass || "col-md-4") + '"><label class="form-label text-muted">' + escapeHtml(label) + '</label><div class="fw-semibold">' + escapeHtml(value) + "</div></div>";
  }

  function noteField(label, value, colClass) {
    return '<div class="' + (colClass || "col-12") + '"><label class="form-label text-muted">' + escapeHtml(label) + '</label><div class="detail-note-box">' + escapeHtml(value) + "</div></div>";
  }

  function section(title, description, bodyHtml) {
    return '<div class="col-12 pt-2"><h5 class="mb-1">' + escapeHtml(title) + '</h5><p class="text-muted mb-0">' + escapeHtml(description) + '</p></div>' + bodyHtml;
  }

  function renderEvidenceList(items, emptyText) {
    if (!(items || []).length) {
      return '<div class="detail-note-box">' + escapeHtml(emptyText) + "</div>";
    }
    return items.map(function (item) {
      return (
        '<a class="detail-note-box text-decoration-none d-block" href="' +
        escapeHtml(item.url || "#") +
        '" target="_blank" rel="noopener">' +
        escapeHtml(item.nome_arquivo) +
        " | Hash: " +
        escapeHtml(item.hash || "-") +
        "</a>"
      );
    }).join("");
  }

  function renderPhotoHashList(items, emptyText) {
    if (!(items || []).length) {
      return '<div class="detail-note-box">' + escapeHtml(emptyText) + "</div>";
    }
    return items.map(function (item) {
      return '<div class="detail-note-box">' + escapeHtml(item.nome_arquivo) + " | Hash: " + escapeHtml(item.hash || "-") + "</div>";
    }).join("");
  }

  function renderPhotoNameList(items, emptyText) {
    if (!(items || []).length) {
      return '<div class="detail-note-box">' + escapeHtml(emptyText) + "</div>";
    }
    return items.map(function (item) {
      return (
        '<a class="detail-note-box text-decoration-none d-block" href="' +
        escapeHtml(item.url || "#") +
        '" target="_blank" rel="noopener">' +
        escapeHtml(item.nome_arquivo) +
        "</a>"
      );
    }).join("");
  }

  function renderSummary(data) {
    var capturaGeo = data.evidencias.geolocalizacao_captura
      ? "Latitude: " + data.evidencias.geolocalizacao_captura.latitude + " | Longitude: " + data.evidencias.geolocalizacao_captura.longitude + " | Hash: " + data.evidencias.geolocalizacao_captura.hash
      : "Não informado";
    var solturaGeo = data.evidencias.geolocalizacao_soltura
      ? "Latitude: " + data.evidencias.geolocalizacao_soltura.latitude + " | Longitude: " + data.evidencias.geolocalizacao_soltura.longitude + " | Hash: " + data.evidencias.geolocalizacao_soltura.hash
      : "Não informado";

    return (
      '<div class="row g-4">' +
      section(
        "Dados do Manejo",
        "Identificação da fauna e contexto inicial do registro.",
        field("Data e hora", data.data_hora) +
          field("Classe", data.classe) +
          field("Nome popular", data.nome_popular) +
          field("Nome científico", data.nome_cientifico, "col-md-6") +
          field("Estágio de desenvolvimento", data.estagio_desenvolvimento, "col-md-6")
      ) +
      section(
        "Captura",
        "Momento inicial do chamado, com contexto do ponto de captura.",
        field("Área", data.area_captura) +
          field("Local", data.local_captura) +
          field("Importância médica", boolLabel(data.importancia_medica)) +
          noteField("Descrição do local", data.descricao_local) +
          noteField("Geolocalização da captura", capturaGeo) +
          '<div class="col-12"><label class="form-label text-muted">Fotos da captura</label><div class="d-grid gap-2">' + renderPhotoHashList(data.evidencias.fotos_captura, "Nenhuma foto de captura registrada.") + "</div></div>"
      ) +
      section(
        "Condução da Soltura",
        "Indicadores da execução do manejo e responsável pela soltura.",
        field("Status", data.status_label) +
          field("Manejo realizado", boolLabel(data.realizado_manejo)) +
          field("Responsável", data.responsavel_manejo)
      ) +
      section(
        "Soltura",
        "Momento final do manejo, com destino e evidências da soltura.",
        field("Área de soltura", data.area_soltura) +
          field("Local de soltura", data.local_soltura) +
          field("Manejo realizado", boolLabel(data.realizado_manejo)) +
          field("Responsável", data.responsavel_manejo) +
          noteField("Descrição do local de soltura", data.descricao_local_soltura) +
          noteField("Geolocalização da soltura", solturaGeo) +
          '<div class="col-12"><label class="form-label text-muted">Fotos da soltura</label><div class="d-grid gap-2">' + renderPhotoHashList(data.evidencias.fotos_soltura, "Nenhuma foto de soltura registrada.") + "</div></div>"
      ) +
      section(
        "Órgão Público",
        "Acionamento institucional vinculado ao registro.",
        field("Acionado", boolLabel(data.acionado_orgao_publico)) +
          field("Órgão público", data.orgao_publico) +
          field("Número do boletim", data.numero_boletim_ocorrencia) +
          noteField("Motivo do acionamento", data.motivo_acionamento)
      ) +
      section(
        "Observações",
        "Informações complementares do manejo.",
        noteField("Observações", data.observacoes)
      ) +
      "</div>"
    );
  }

  function renderEvidence(data) {
    return (
      '<div class="mb-3"><label class="form-label text-muted">Fotos de captura</label><div class="fw-semibold">' + escapeHtml(String(data.evidencias.fotos_captura_count || 0)) + "</div></div>" +
      '<div class="mb-3"><label class="form-label text-muted">Fotos de soltura</label><div class="fw-semibold">' + escapeHtml(String(data.evidencias.fotos_soltura_count || 0)) + "</div></div>" +
      '<div class="mb-3"><label class="form-label text-muted">Fotos Captura</label><div class="d-grid gap-2">' + renderPhotoNameList(data.evidencias.fotos_captura, "Nenhuma foto de captura registrada.") + '</div></div>' +
      '<div class="mb-0"><label class="form-label text-muted">Fotos Soltura</label><div class="d-grid gap-2">' + renderPhotoNameList(data.evidencias.fotos_soltura, "Nenhuma foto de soltura registrada.") + "</div></div>"
    );
  }

  function renderAudit(data) {
    return (
      '<div class="mb-3"><label class="form-label text-muted">ID</label><div class="fw-semibold">#' + escapeHtml(data.id) + "</div></div>" +
      '<div class="mb-3"><label class="form-label text-muted">Criado em</label><div class="fw-semibold">' + escapeHtml(data.criado_em) + "</div></div>" +
      '<div class="mb-3"><label class="form-label text-muted">Criado por</label><div class="fw-semibold">' + escapeHtml(data.criado_por) + "</div></div>" +
      '<div class="mb-3"><label class="form-label text-muted">Atualizado em</label><div class="fw-semibold">' + escapeHtml(data.modificado_em) + "</div></div>" +
      '<div class="mb-0"><label class="form-label text-muted">Atualizado por</label><div class="fw-semibold">' + escapeHtml(data.modificado_por) + "</div></div>"
    );
  }

  function initManejoView() {
    var contentNode = document.getElementById("manejo-view-content");
    var evidenceNode = document.getElementById("manejo-evidence-content");
    var auditNode = document.getElementById("manejo-audit-content");
    if (!contentNode || !evidenceNode || !auditNode) return;
    var apiUrl = contentNode.dataset.apiUrl;
    if (!apiUrl) return;

    fetch(apiUrl, { headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then(function (response) {
        return response.json().then(function (payload) {
          return { response: response, payload: payload };
        });
      })
      .then(function (result) {
        if (!result.response.ok || !result.payload.ok) {
          throw new Error("Falha ao carregar manejo.");
        }
        var data = result.payload.data || {};
        contentNode.innerHTML = renderSummary(data);
        evidenceNode.innerHTML = renderEvidence(data);
        auditNode.innerHTML = renderAudit(data);
      })
      .catch(function () {
        contentNode.innerHTML = '<div class="text-muted">Não foi possível carregar o resumo do manejo.</div>';
        evidenceNode.innerHTML = '<div class="text-muted">Não foi possível carregar as fotos.</div>';
        auditNode.innerHTML = '<div class="text-muted">Não foi possível carregar a auditoria.</div>';
      });
  }

  document.addEventListener("DOMContentLoaded", initManejoView);
})();
