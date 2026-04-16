(function () {
  function fillLocalOptions(select, items, selectedValue) {
    const options = ['<option value="">Selecione...</option>'];
    items.forEach((item) => {
      const selected = selectedValue && selectedValue === item.chave ? ' selected' : '';
      options.push(`<option value="${item.chave}"${selected}>${item.valor}</option>`);
    });
    select.innerHTML = options.join('');
  }

  async function updateLocais(areaSelect, localSelect) {
    const area = areaSelect.value;
    if (!area) {
      localSelect.innerHTML = '<option value="">Selecione a área primeiro...</option>';
      return;
    }
    const url = `${areaSelect.dataset.localUrl}?area=${encodeURIComponent(area)}`;
    const response = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
    if (!response.ok) {
      throw new Error('Falha ao carregar locais.');
    }
    const payload = await response.json();
      const items = payload && payload.data && payload.data.locais ? payload.data.locais : [];
    fillLocalOptions(localSelect, items, localSelect.dataset.selected || '');
  }

  function syncSetor(colaboradorSelect, setorInput) {
    const option = colaboradorSelect.options[colaboradorSelect.selectedIndex];
      setorInput.value = option && option.dataset && option.dataset.setor ? option.dataset.setor : '';
  }

  function syncColaboradorMode(organicoSelect, colaboradorSelect, colaboradorText, setorInput) {
    if (!organicoSelect || !colaboradorSelect || !colaboradorText || !setorInput) {
      return;
    }

    const isOrganico = organicoSelect.value !== 'false';
    if (isOrganico) {
      colaboradorSelect.disabled = false;
      colaboradorSelect.name = 'colaborador';
      colaboradorSelect.classList.remove('d-none');
      colaboradorText.disabled = true;
      colaboradorText.name = '';
      colaboradorText.classList.add('d-none');
      setorInput.readOnly = true;
      syncSetor(colaboradorSelect, setorInput);
      return;
    }

    colaboradorText.value = colaboradorText.value || '';
    colaboradorSelect.disabled = true;
    colaboradorSelect.name = '';
    colaboradorSelect.classList.add('d-none');
    colaboradorText.disabled = false;
    colaboradorText.name = 'colaborador';
    colaboradorText.classList.remove('d-none');
    setorInput.readOnly = false;
  }

  function buildStatusOptions(statusSelect) {
    return Array.from(statusSelect.options).map((option) => ({
      value: option.value,
      label: option.textContent,
    }));
  }

  function fillStatusOptions(statusSelect, options, selectedValue) {
    statusSelect.innerHTML = options
      .map((option) => {
        const selected = selectedValue === option.value ? ' selected' : '';
        return `<option value="${option.value}"${selected}>${option.label}</option>`;
      })
      .join('');
  }

  function syncStatusWithSituacao(situacaoSelect, statusSelect, allStatusOptions) {
    if (!situacaoSelect || !statusSelect) {
      return;
    }

    if (situacaoSelect.value === 'perdido') {
      const perdidoOptions = allStatusOptions.filter((option) => option.value === '' || option.value === 'perdido');
      fillStatusOptions(statusSelect, perdidoOptions, 'perdido');
      statusSelect.value = 'perdido';
      statusSelect.disabled = true;
      statusSelect.setAttribute('title', 'Quando a situação é Perdido, o status também é Perdido.');
      return;
    }

    const achadoOptions = allStatusOptions.filter((option) => option.value !== 'perdido');
    const currentValue = statusSelect.value === 'perdido' ? '' : statusSelect.value;
    fillStatusOptions(statusSelect, achadoOptions, currentValue);
    statusSelect.disabled = false;
    statusSelect.removeAttribute('title');
  }

  function initSignatureCapture(statusSelect) {
    const signatureSection = document.getElementById('id_assinatura_section');
    const signatureInput = document.getElementById('id_assinatura_entrega');
    const signatureStatus = document.getElementById('id_assinatura_status');
    const openButton = document.getElementById('id_assinatura_abrir');
    const clearButton = document.getElementById('id_assinatura_limpar');
    const modalElement = document.getElementById('achadosSignatureModal');
    const canvas = document.getElementById('achadosSignatureCanvas');
    const modalClearButton = document.getElementById('achadosSignatureClear');
    const modalSaveButton = document.getElementById('achadosSignatureSave');

    if (!statusSelect || !signatureSection || !signatureInput || !signatureStatus || !openButton || !clearButton || !modalElement || !canvas || !modalClearButton || !modalSaveButton) {
      return;
    }

    const modal = window.bootstrap ? new window.bootstrap.Modal(modalElement) : null;
    const ctx = canvas.getContext('2d');
    let drawing = false;
    let hasStroke = false;
    let loadedSignatureDataUrl = '';

    function drawGuideLine() {
      ctx.beginPath();
      ctx.strokeStyle = '#cbd5e1';
      ctx.lineWidth = 1;
      ctx.moveTo(72, canvas.height - 78);
      ctx.lineTo(canvas.width - 72, canvas.height - 78);
      ctx.stroke();
    }

    function resizeCanvas() {
      const ratio = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      const width = Math.max(Math.floor(rect.width * ratio), 1);
      const height = Math.max(Math.floor(rect.height * ratio), 1);

      if (canvas.width === width && canvas.height === height) {
        return;
      }

      const previousDataUrl = hasStroke ? canvas.toDataURL('image/png') : loadedSignatureDataUrl;
      canvas.width = width;
      canvas.height = height;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      resetCanvas();

      if (previousDataUrl) {
        const image = new Image();
        image.onload = function () {
          ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
          hasStroke = true;
          loadedSignatureDataUrl = previousDataUrl;
        };
        image.src = previousDataUrl;
      }
    }

    function resetCanvas() {
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      drawGuideLine();
      ctx.lineWidth = 2.4;
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';
      ctx.strokeStyle = '#111827';
      hasStroke = false;
    }

    function positionFromEvent(event) {
      const rect = canvas.getBoundingClientRect();
      const source = event.touches ? event.touches[0] : event;
      const scaleX = canvas.width / rect.width;
      const scaleY = canvas.height / rect.height;
      return {
        x: (source.clientX - rect.left) * scaleX,
        y: (source.clientY - rect.top) * scaleY,
      };
    }

    function updateSignatureStatus() {
      if (signatureInput.value) {
        signatureStatus.textContent = 'Assinatura capturada e pronta para salvar.';
        signatureStatus.className = 'small mt-2 text-success';
        return;
      }
      signatureStatus.textContent = 'Nenhuma assinatura capturada.';
      signatureStatus.className = 'small mt-2 text-muted';
    }

    function syncSignatureVisibility() {
      const required = statusSelect.value === 'entregue';
      signatureSection.classList.toggle('d-none', !required);
      if (!required) {
        signatureInput.value = '';
        updateSignatureStatus();
      }
    }

    function startDraw(event) {
      drawing = true;
      const pos = positionFromEvent(event);
      ctx.beginPath();
      ctx.moveTo(pos.x, pos.y);
      event.preventDefault();
    }

    function draw(event) {
      if (!drawing) return;
      const pos = positionFromEvent(event);
      ctx.lineTo(pos.x, pos.y);
      ctx.stroke();
      hasStroke = true;
      event.preventDefault();
    }

    function endDraw() {
      drawing = false;
    }

    resetCanvas();
    updateSignatureStatus();
    syncSignatureVisibility();

    openButton.addEventListener('click', function () {
      loadedSignatureDataUrl = signatureInput.value || '';
      resizeCanvas();
      if (signatureInput.value) {
        const image = new Image();
        image.onload = function () {
          resetCanvas();
          ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
          hasStroke = true;
        };
        image.src = signatureInput.value;
      }
      if (modal) {
        modal.show();
      }
    });

    clearButton.addEventListener('click', function () {
      signatureInput.value = '';
      loadedSignatureDataUrl = '';
      updateSignatureStatus();
    });

    modalClearButton.addEventListener('click', function () {
      loadedSignatureDataUrl = '';
      resetCanvas();
    });

    modalSaveButton.addEventListener('click', function () {
      if (!hasStroke) {
        signatureStatus.textContent = 'Faça a assinatura antes de confirmar.';
        signatureStatus.className = 'small mt-2 text-danger';
        return;
      }
      signatureInput.value = canvas.toDataURL('image/png');
      loadedSignatureDataUrl = signatureInput.value;
      updateSignatureStatus();
      if (modal) {
        modal.hide();
      }
    });

    canvas.addEventListener('mousedown', startDraw);
    canvas.addEventListener('mousemove', draw);
    canvas.addEventListener('mouseup', endDraw);
    canvas.addEventListener('mouseleave', endDraw);
    canvas.addEventListener('touchstart', startDraw, { passive: false });
    canvas.addEventListener('touchmove', draw, { passive: false });
    canvas.addEventListener('touchend', endDraw);
    if (modalElement) {
      modalElement.addEventListener('shown.bs.modal', resizeCanvas);
    }
    window.addEventListener('resize', function () {
      if (signatureInput.value || modalElement.classList.contains('show')) {
        resizeCanvas();
      }
    });

    statusSelect.addEventListener('change', syncSignatureVisibility);
  }

  function initAsyncAchadosList() {
    if (!window.SiopAsyncList) {
      return;
    }

    window.SiopAsyncList.initAsyncList({
      formSelector: '#achados-perdidos-list-form',
      tableBodySelector: '#achados-perdidos-list-body',
      metaSelector: '#achados-perdidos-list-meta',
      paginationSelector: '#achados-perdidos-list-pagination',
      dataKey: 'itens',
      columnCount: 8,
      emptyMessage: 'Nenhum registro encontrado.',
      metaText: function (total) {
        return total + (total === 1 ? ' item encontrado.' : ' itens encontrados.');
      },
      renderRow: function (item) {
        var escapeHtml = window.SiopAsyncList.escapeHtml;
        var statusHtml =
          '<span class="badge ' +
          (item.status === 'recebido' ? 'badge-warning' : 'badge-success') +
          '">' +
          escapeHtml(item.status_label || '-') +
          '</span>';
        return (
          '<tr>' +
          '<td>#' + item.id + '</td>' +
          '<td>' + escapeHtml(item.situacao_label || '-') + '</td>' +
          '<td>' + escapeHtml(item.tipo_label || '-') + '</td>' +
          '<td>' + escapeHtml(item.area_label || '-') + '</td>' +
          '<td>' + escapeHtml(item.local_label || '-') + '</td>' +
          '<td>' + statusHtml + '</td>' +
          '<td>' + escapeHtml(item.criado_em || '-') + '</td>' +
          '<td class="text-end"><a href="' + escapeHtml(item.view_url || '#') + '" class="btn btn-sm btn-label-info">Ver</a></td>' +
          '</tr>'
        );
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    const areaSelect = document.getElementById('id_area');
    const localSelect = document.getElementById('id_local');
    const organicoSelect = document.getElementById('id_organico');
    const colaboradorSelect = document.getElementById('id_colaborador_select');
    const colaboradorText = document.getElementById('id_colaborador_text');
    const setorInput = document.getElementById('id_setor');
    const situacaoSelect = document.getElementById('id_situacao');
    const statusSelect = document.getElementById('id_status');

    if (areaSelect && localSelect) {
      localSelect.dataset.selected = localSelect.value;
      areaSelect.addEventListener('change', function () {
        localSelect.dataset.selected = '';
        updateLocais(areaSelect, localSelect).catch(function () {
          localSelect.innerHTML = '<option value="">Selecione a área primeiro...</option>';
        });
      });
    }

    if (organicoSelect && colaboradorSelect && colaboradorText && setorInput) {
      syncColaboradorMode(organicoSelect, colaboradorSelect, colaboradorText, setorInput);
      syncSetor(colaboradorSelect, setorInput);
      organicoSelect.addEventListener('change', function () {
        syncColaboradorMode(organicoSelect, colaboradorSelect, colaboradorText, setorInput);
      });
      colaboradorSelect.addEventListener('change', function () {
        syncSetor(colaboradorSelect, setorInput);
      });
    }

    if (situacaoSelect && statusSelect) {
      const allStatusOptions = buildStatusOptions(statusSelect);
      syncStatusWithSituacao(situacaoSelect, statusSelect, allStatusOptions);

      situacaoSelect.addEventListener('change', function () {
        syncStatusWithSituacao(situacaoSelect, statusSelect, allStatusOptions);
      });
    }

    if (statusSelect) {
      initSignatureCapture(statusSelect);
    }
    initAsyncAchadosList();
  });
})();
