(function () {
  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function field(label, value, colClass) {
    return '<div class="' + (colClass || "col-md-4") + '"><label class="form-label text-muted">' + escapeHtml(label) + '</label><div class="fw-semibold">' + escapeHtml(value) + "</div></div>";
  }

  function noteField(label, value, colClass) {
    return '<div class="' + (colClass || "col-md-6") + '"><label class="form-label text-muted">' + escapeHtml(label) + '</label><div class="detail-note-box">' + escapeHtml(value) + "</div></div>";
  }

  function section(title, description, bodyHtml) {
    return '<div class="col-12 pt-2"><h5 class="mb-1">' + escapeHtml(title) + '</h5><p class="text-muted mb-0">' + escapeHtml(description) + "</p></div>" + bodyHtml;
  }

  function renderPhotoNameList(items, emptyText) {
    if (!(items || []).length) return '<div class="detail-note-box">' + escapeHtml(emptyText) + "</div>";
    return items.map(function (item) {
      return '<a class="detail-note-box text-decoration-none d-block" href="' + escapeHtml(item.url || "#") + '" target="_blank" rel="noopener">' + escapeHtml(item.nome_arquivo) + "</a>";
    }).join("");
  }

  function renderPhotoHashList(items, emptyText) {
    if (!(items || []).length) return '<div class="detail-note-box">' + escapeHtml(emptyText) + "</div>";
    return items.map(function (item) {
      return '<div class="detail-note-box">' + escapeHtml(item.nome_arquivo + " | Hash: " + item.hash) + "</div>";
    }).join("");
  }

  function renderSummary(data) {
    var geoText = data.evidencias.geolocalizacao
      ? "Latitude: " + data.evidencias.geolocalizacao.latitude + " | Longitude: " + data.evidencias.geolocalizacao.longitude + " | Hash: " + data.evidencias.geolocalizacao.hash
      : "Nenhuma geolocalização registrada.";
    return (
      '<div class="row g-4">' +
      section("Identificação da Ocorrência", "Contexto principal, local e classificação do registro.", field("Data e Hora do Registro", data.data_hora_inicio) + field("Data e Hora de Encerramento", data.data_hora_fim) + '<div class="col-md-4"><label class="form-label text-muted">Status</label><div><span class="badge badge-' + escapeHtml(data.status_badge) + '">' + escapeHtml(data.status_label) + "</span></div></div>" + field("Responsável pelo Registro", data.responsavel_registro, "col-md-6") + field("Responsável Técnico", data.responsavel_tecnico) + field("Área", data.area) + field("Local", data.local) + field("Tipo de Himenóptero", data.tipo_himenoptero) + field("Nome Popular", data.popular) + field("Espécie", data.especie) + field("Proximidade de pessoas", data.proximidade_pessoas) + field("Classificação do Risco", data.classificacao_risco) + field("Condição", data.condicao) + field("Ação Realizada", data.acao_realizada) + field("Isolamento de Área", data.isolamento_area)) +
      section("Observações Técnicas", "Descrição do local, observações gerais e justificativa técnica.", noteField("Descrição do Local", data.descricao_local, "col-12") + noteField("Observações", data.observacao, "col-12") + noteField("Justificativa Técnica", data.justificativa_tecnica, "col-12")) +
      section("Anexos e Evidências", "Geolocalização e hashes das imagens vinculadas ao registro.", '<div class="col-12"><label class="form-label text-muted">Geolocalização</label><div class="detail-note-box">' + escapeHtml(geoText) + '</div></div>' + '<div class="col-12"><label class="form-label text-muted">Fotos</label><div class="d-grid gap-2">' + renderPhotoHashList(data.evidencias.fotos, "Nenhuma foto registrada.") + "</div></div>") +
      "</div>"
    );
  }

  function renderEvidence(data) {
    return '<div class="mb-0"><label class="form-label text-muted">Fotos</label><div class="d-grid gap-2">' + renderPhotoNameList(data.evidencias.fotos, "Nenhuma foto registrada.") + "</div></div>";
  }

  function renderAudit(data) {
    return '<div class="mb-3"><label class="form-label text-muted">ID</label><div class="fw-semibold">#' + escapeHtml(data.id) + '</div></div>' + '<div class="mb-3"><label class="form-label text-muted">Criado em</label><div class="fw-semibold">' + escapeHtml(data.criado_em) + '</div></div>' + '<div class="mb-3"><label class="form-label text-muted">Criado por</label><div class="fw-semibold">' + escapeHtml(data.criado_por) + '</div></div>' + '<div class="mb-3"><label class="form-label text-muted">Atualizado em</label><div class="fw-semibold">' + escapeHtml(data.modificado_em) + '</div></div>' + '<div class="mb-0"><label class="form-label text-muted">Atualizado por</label><div class="fw-semibold">' + escapeHtml(data.modificado_por) + "</div></div>";
  }

  function initHimenopterosView() {
    var contentNode = document.getElementById("himenopteros-view-content");
    var evidenceNode = document.getElementById("himenopteros-evidence-content");
    var auditNode = document.getElementById("himenopteros-audit-content");
    if (!contentNode || !evidenceNode || !auditNode) return;
    var apiUrl = contentNode.dataset.apiUrl;
    if (!apiUrl) return;
    window.fetch(apiUrl, { headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then(function (response) { return response.json().then(function (payload) { return { response: response, payload: payload }; }); })
      .then(function (result) {
        if (!result.response.ok || !result.payload.ok) throw new Error("Falha ao carregar registro.");
        var data = result.payload.data || {};
        contentNode.innerHTML = renderSummary(data);
        evidenceNode.innerHTML = renderEvidence(data);
        auditNode.innerHTML = renderAudit(data);
      })
      .catch(function () {
        contentNode.innerHTML = '<div class="text-muted">Não foi possível carregar o resumo do registro.</div>';
        evidenceNode.innerHTML = '<div class="text-muted">Não foi possível carregar as evidências.</div>';
        auditNode.innerHTML = '<div class="text-muted">Não foi possível carregar a auditoria.</div>';
      });
  }

  document.addEventListener("DOMContentLoaded", initHimenopterosView);
})();
