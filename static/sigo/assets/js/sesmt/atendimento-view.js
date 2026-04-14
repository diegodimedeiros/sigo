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

  function valueOr(value, fallback) {
    var normalized = String(value == null ? "" : value).trim();
    return normalized || fallback;
  }

  function field(label, value, colClass) {
    return (
      '<div class="' + (colClass || "col-md-4") + '"><label class="form-label text-muted">' +
      escapeHtml(label) +
      '</label><div class="fw-semibold">' +
      escapeHtml(value) +
      "</div></div>"
    );
  }

  function noteField(label, value, colClass) {
    return (
      '<div class="' + (colClass || "col-md-6") + '"><label class="form-label text-muted">' +
      escapeHtml(label) +
      '</label><div class="detail-note-box">' +
      escapeHtml(value) +
      "</div></div>"
    );
  }

  function section(title, description, bodyHtml) {
    return (
      '<div class="col-12 pt-2"><h5 class="mb-1">' + escapeHtml(title) + '</h5><p class="text-muted mb-0">' +
      escapeHtml(description) +
      '</p></div>' +
      bodyHtml
    );
  }

  function renderWitnesses(data) {
    if (!(data.testemunhas || []).length) {
      return '<div class="col-12"><div class="detail-note-box">Nenhuma testemunha registrada.</div></div>';
    }
    var items = data.testemunhas.map(function (t) {
      return (
        '<div class="border rounded-3 p-3"><div class="row g-3">' +
        field("Nome", valueOr(t.nome, "-")) +
        field("Documento", valueOr(t.documento, "-"), "col-md-3") +
        field("Telefone", valueOr(t.telefone, "-"), "col-md-3") +
        field("Nascimento", valueOr(t.data_nascimento, "-"), "col-md-2") +
        "</div></div>"
      );
    }).join("");
    return '<div class="col-12"><div class="d-grid gap-3">' + items + "</div></div>";
  }

  function renderEvidenceList(items, emptyText) {
    if (!(items || []).length) {
      return '<div class="detail-note-box">' + escapeHtml(emptyText) + "</div>";
    }
    return items.map(function (item) {
      return '<div class="detail-note-box">' + escapeHtml(item.nome_arquivo + " | Hash: " + item.hash) + "</div>";
    }).join("");
  }

  function renderEvidenceNameList(items, emptyText) {
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

  function renderSignaturePreviewList(items, emptyText) {
    if (!(items || []).length) {
      return '<div class="detail-note-box">' + escapeHtml(emptyText) + "</div>";
    }
    return items.map(function (item) {
      return (
        '<a class="detail-note-box text-decoration-none d-block" href="' +
        escapeHtml(item.url || "#") +
        '" target="_blank" rel="noopener">' +
        '<div class="mb-2 fw-semibold">' + escapeHtml(item.nome_arquivo) + "</div>" +
        '<div class="border rounded-3 bg-white overflow-hidden" style="min-height: 140px;">' +
        '<img src="' + escapeHtml(item.url || "#") + '" alt="' + escapeHtml(item.nome_arquivo) + '" style="display:block;width:100%;height:auto;max-height:220px;object-fit:contain;background:#fff;" />' +
        "</div></a>"
      );
    }).join("");
  }

  function renderSummary(data) {
    var empty = data.empty_label || "-";
    var geoText = empty;
    if (data.evidencias.geolocalizacao_principal) {
      geoText =
        "Latitude: " +
        data.evidencias.geolocalizacao_principal.latitude +
        " | Longitude: " +
        data.evidencias.geolocalizacao_principal.longitude +
        " | Hash: " +
        data.evidencias.geolocalizacao_principal.hash;
    }

    return (
      '<div class="row g-4">' +
      section(
        "Dados da Pessoa",
        "Identificação principal da pessoa atendida.",
        field("Tipo de pessoa", valueOr(data.tipo_pessoa_label, "-")) +
          field("Recusa de atendimento", boolLabel(data.recusa_atendimento)) +
          '<div class="col-md-4"><label class="form-label text-muted">Status</label><div><span class="badge badge-' + escapeHtml(data.status_badge || "info") + '">' + escapeHtml(valueOr(data.status_label, "-")) + "</span></div></div>" +
          field("Nome completo", valueOr(data.pessoa.nome, "-"), "col-md-6") +
          field("Documento", valueOr(data.pessoa.documento, empty), "col-md-3") +
          field("Órgão emissor", valueOr(data.pessoa.orgao_emissor, empty), "col-md-3") +
          field("Sexo", valueOr(data.pessoa.sexo, empty)) +
          field("Data de nascimento", valueOr(data.pessoa.data_nascimento, empty)) +
          field("Nacionalidade", valueOr(data.pessoa.nacionalidade, empty))
      ) +
      section(
        "Contato",
        "Dados de contato e endereço vinculados ao atendimento.",
        field("Telefone", valueOr(data.contato.telefone, empty), "col-md-6") +
          field("E-mail", valueOr(data.contato.email, empty), "col-md-6") +
          field("Endereço", valueOr(data.contato.endereco, empty), "col-md-6") +
          field("Bairro", valueOr(data.contato.bairro, empty), "col-md-6") +
          field("Cidade", valueOr(data.contato.cidade, empty)) +
          field("Estado", valueOr(data.contato.estado, empty)) +
          field("Província", valueOr(data.contato.provincia, empty)) +
          field("País", valueOr(data.contato.pais, empty))
      ) +
      section(
        "Dados do Atendimento",
        "Contexto operacional, tipo e responsável assistencial.",
        field("Data e hora", valueOr(data.data_atendimento, "-")) +
          field("Área de atendimento", valueOr(data.area_atendimento_label, "-")) +
          field("Local", valueOr(data.local_label, "-")) +
          field("Tipo de ocorrência", valueOr(data.tipo_ocorrencia_label, "-")) +
          field("Responsável pelo atendimento", valueOr(data.responsavel_atendimento, "-")) +
          field("Atendimento realizado", boolLabel(data.atendimentos)) +
          field("Primeiros socorros", valueOr(data.primeiros_socorros_label, empty))
      ) +
      section(
        "Saúde",
        "Informações clínicas e de plano de saúde.",
        field("Doença preexistente", boolLabel(data.doenca_preexistente)) +
          field("Alergia", boolLabel(data.alergia)) +
          field("Possui plano de saúde", boolLabel(data.plano_saude)) +
          noteField("Descrição da doença", valueOr(data.descricao_doenca, empty)) +
          noteField("Descrição da alergia", valueOr(data.descricao_alergia, empty)) +
          field("Nome do plano de saúde", valueOr(data.nome_plano_saude, empty), "col-md-6") +
          field("Número da carteirinha", valueOr(data.numero_carteirinha, empty), "col-md-6")
      ) +
      section(
        "Destino",
        "Informações sobre o destino ou remoção do atendimento.",
        field("Seguiu para o passeio", boolLabel(data.seguiu_passeio)) +
          field("Houve remoção", boolLabel(data.houve_remocao)) +
          field("Transporte", valueOr(data.transporte_label, empty)) +
          field("Encaminhamento", valueOr(data.encaminhamento_label, empty)) +
          field("Hospital", valueOr(data.hospital, empty)) +
          field("Médico responsável", valueOr(data.medico_responsavel, empty)) +
          field("CRM", valueOr(data.crm, empty))
      ) +
      section(
        "Acompanhante",
        "Dados do acompanhante, quando houver.",
        field("Possui acompanhante", boolLabel(data.possui_acompanhante)) +
          field("Nome", valueOr(data.acompanhante.nome, empty)) +
          field("Documento", valueOr(data.acompanhante.documento, empty)) +
          field("Sexo", valueOr(data.acompanhante.sexo, empty)) +
          field("Parentesco", valueOr(data.acompanhante.parentesco, empty))
      ) +
      section("Testemunhas", "Registros vinculados ao atendimento.", renderWitnesses(data)) +
      section(
        "Anexos e Evidências",
        "Geolocalização principal e hashes dos arquivos vinculados ao atendimento.",
        '<div class="col-12"><label class="form-label text-muted">Geolocalização principal</label><div class="detail-note-box">' + escapeHtml(geoText) + '</div></div>' +
        '<div class="col-12"><label class="form-label text-muted">Fotos registradas</label><div class="d-grid gap-2">' + renderEvidenceList(data.evidencias.fotos, data.recusa_atendimento ? "Não informado" : "Nenhuma foto registrada.") + '</div></div>' +
        '<div class="col-12"><label class="form-label text-muted">Assinatura do atendido</label><div class="d-grid gap-2">' + renderEvidenceList(data.evidencias.assinaturas, data.recusa_atendimento ? "Não informado" : "Nenhuma assinatura registrada.") + '</div></div>'
      ) +
      section(
        "Descrição",
        "Relato assistencial e contexto do atendimento.",
        '<div class="col-12"><label class="form-label text-muted">Descrição do atendimento</label><div class="detail-note-box">' + escapeHtml(valueOr(data.descricao, "-")) + "</div></div>"
      ) +
      "</div>"
    );
  }

  function renderEvidence(data) {
    return (
      '<div class="mb-3"><label class="form-label text-muted">Fotos</label><div class="fw-semibold">' + escapeHtml(String(data.evidencias.fotos_count || 0)) + "</div></div>" +
      '<div class="mb-3"><label class="form-label text-muted">Geolocalização</label><div class="fw-semibold">' + escapeHtml(boolLabel(!!data.evidencias.geolocalizacao)) + "</div></div>" +
      '<div class="mb-3"><label class="form-label text-muted">Assinaturas</label><div class="fw-semibold">' + escapeHtml(String(data.evidencias.assinaturas_count || 0)) + "</div></div>" +
      '<div class="mb-3"><label class="form-label text-muted">Fotos</label><div class="d-grid gap-2">' + renderEvidenceNameList(data.evidencias.fotos, data.recusa_atendimento ? "Não informado" : "Nenhuma foto registrada.") + '</div></div>' +
      '<div class="mb-0"><label class="form-label text-muted">Assinaturas</label><div class="d-grid gap-2">' + renderSignaturePreviewList(data.evidencias.assinaturas, data.recusa_atendimento ? "Não informado" : "Nenhuma assinatura registrada.") + "</div></div>"
    );
  }

  function renderAudit(data) {
    return (
      '<div class="mb-3"><label class="form-label text-muted">ID</label><div class="fw-semibold">#' + escapeHtml(data.id) + "</div></div>" +
      '<div class="mb-3"><label class="form-label text-muted">Hash do atendimento</label><div class="detail-note-box">' + escapeHtml(valueOr(data.hash_atendimento, "-")) + "</div></div>" +
      '<div class="mb-3"><label class="form-label text-muted">Criado em</label><div class="fw-semibold">' + escapeHtml(valueOr(data.criado_em, "-")) + "</div></div>" +
      '<div class="mb-3"><label class="form-label text-muted">Criado por</label><div class="fw-semibold">' + escapeHtml(valueOr(data.criado_por, "-")) + "</div></div>" +
      '<div class="mb-3"><label class="form-label text-muted">Atualizado em</label><div class="fw-semibold">' + escapeHtml(valueOr(data.modificado_em, "-")) + "</div></div>" +
      '<div class="mb-0"><label class="form-label text-muted">Atualizado por</label><div class="fw-semibold">' + escapeHtml(valueOr(data.modificado_por, "-")) + "</div></div>"
    );
  }

  function initAtendimentoView() {
    var contentNode = document.getElementById("atendimento-view-content");
    var evidenceNode = document.getElementById("atendimento-evidence-content");
    var auditNode = document.getElementById("atendimento-audit-content");
    if (!contentNode || !evidenceNode || !auditNode) {
      return;
    }
    var apiUrl = contentNode.dataset.apiUrl;
    if (!apiUrl) {
      return;
    }
    window.fetch(apiUrl, {
      headers: {
        "X-Requested-With": "XMLHttpRequest"
      }
    })
      .then(function (response) {
        return response.json().then(function (payload) {
          return { response: response, payload: payload };
        });
      })
      .then(function (result) {
        if (!result.response.ok || !result.payload.ok) {
          throw new Error("Falha ao carregar atendimento.");
        }
        var data = result.payload.data || {};
        contentNode.innerHTML = renderSummary(data);
        evidenceNode.innerHTML = renderEvidence(data);
        auditNode.innerHTML = renderAudit(data);
      })
      .catch(function () {
        contentNode.innerHTML = '<div class="text-muted">Não foi possível carregar o resumo do atendimento.</div>';
        evidenceNode.innerHTML = '<div class="text-muted">Não foi possível carregar as evidências.</div>';
        auditNode.innerHTML = '<div class="text-muted">Não foi possível carregar a auditoria.</div>';
      });
  }

  document.addEventListener("DOMContentLoaded", initAtendimentoView);
})();
