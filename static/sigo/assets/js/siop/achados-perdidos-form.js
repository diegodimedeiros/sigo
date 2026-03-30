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
    const items = payload?.data?.locais || [];
    fillLocalOptions(localSelect, items, localSelect.dataset.selected || '');
  }

  function syncSetor(colaboradorSelect, setorInput) {
    const option = colaboradorSelect.options[colaboradorSelect.selectedIndex];
    setorInput.value = option?.dataset?.setor || '';
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
  });
})();
