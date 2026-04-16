# Padrão de Criação de JavaScript - SIOP

## Visão Geral

Este documento define o padrão **oficial e obrigatório** para criação de arquivos JavaScript no projeto SIGO. O padrão é baseado no **SIOP** (módulo de Segurança/Acesso), que serve como referência de excelência para código modular, reutilizável e mantível.

**Objetivo**: Garantir consistência, reduzir duplicação de código e facilitar manutenção e testes.

---

## 1. Estrutura de Diretórios e Nomenclatura de Arquivos

### Padrão de Nomes: `<modulo>-<feature>-<tipo>.js`

```
/static/sigo/assets/js/
├── core/                           # Dependências externas
│   ├── bootstrap.min.js
│   ├── jquery-3.7.1.min.js
│   └── popper.min.js
│
├── plugin/                          # Plugins de terceiros
│   ├── chart.js/
│   └── jquery-scrollbar/
│
├── sigo/                            # Módulo SIGO (core UI/framework)
│   ├── csrf.js                      # CSRF protection
│   ├── sigo-app.js                  # Main application setup
│   ├── sigo-theme-init.js           # Theme system
│   └── ...
│
├── sesmt/                           # Módulo SESMT
│   ├── core/                        # Core reutilizáveis do SESMT
│   │   ├── async-export.js          # Export handler reutilizável
│   │   ├── photo-manager.js         # Photo/evidence management
│   │   └── geolocation.js           # Geolocation handling
│   ├── atendimento-form.js          # Feature: atendimento (form)
│   ├── atendimento-view.js          # Feature: atendimento (view)
│   ├── atendimento-export.js        # Feature: atendimento (export)
│   ├── flora-form.js
│   ├── flora-view.js
│   ├── flora-export.js
│   ├── himenopteros-form.js
│   ├── himenopteros-view.js
│   ├── himenopteros-export.js
│   ├── manejo-form.js
│   ├── manejo-view.js
│   └── manejo-export.js
│
└── siop/                            # Módulo SIOP
    ├── async-form.js                # Core: reusable async form handler
    ├── async-list.js                # Core: reusable list pagination
    ├── acesso-colaboradores-form.js # Feature files
    ├── acesso-terceiros-form.js
    ├── achados-perdidos-form.js
    └── ...
```

### Convenções de Nomenclatura

| Tipo | Padrão | Propósito | Exemplo |
|------|--------|----------|---------|
| **Form** | `<feature>-form.js` | Manipulação de formulários, submissão async, validação | `atendimento-form.js` |
| **View** | `<feature>-view.js` | Renderização de detalhes, formatação de dados | `flora-view.js` |
| **Export** | `<feature>-export.js` | CSV/Excel download, gestão de ficheiros | `manejo-export.js` |
| **Core** | `<funcionalidade>.js` | Módulos reutilizáveis entre features | `async-export.js`, `photo-manager.js` |
| **Utility** | `<funcionalidade>.js` | Helpers, configuração global | `csrf.js`, `sigo-theme-init.js` |

---

## 2. Estrutura Interna de Arquivos

### 2.1 Padrão IIFE (Immediately Invoked Function Expression)

**Todo arquivo JavaScript deve usar o padrão IIFE para criar scope isolado**:

```javascript
(function () {
  // Código privado - não acessível globalmente
  function privateHelper() {
    // ...
  }

  // API pública - exposta no window
  window.MinhaAPI = {
    publicMethod: function () { }
  };
})();
```

**Razões**:
- ✓ Previne poluição do namespace global
- ✓ Encapsulamento: funções privadas não são expostas
- ✓ Evita conflitos de nomes entre arquivos
- ✓ Facilita garbage collection

---

### 2.2 Organização de Funções dentro do Arquivo

**Ordem recomendada** (do menos ao mais específico):

```javascript
(function () {
  // 1. CONSTANTES e CONFIGURAÇÕES
  var MAX_FILE_SIZE = 5 * 1024 * 1024;  // 5 MB
  var VALID_EXTENSIONS = ["jpg", "png"];

  // 2. FUNÇÕES HELPER (utilitários, sem dependência do DOM)
  function escapeHtml(value) {
    return String(value || "").replace(/&/g, "&amp;");
  }

  function fileSignature(file) {
    return [file.name, file.size, file.type].join("::");
  }

  // 3. FUNÇÕES DE SELEÇÃO DO DOM
  function resolveForm(formId) {
    return document.getElementById(formId);
  }

  function getFeedbackBox(form) {
    return form ? form.querySelector(".js-form-feedback") : null;
  }

  // 4. FUNÇÕES DE MANIPULAÇÃO DO DOM
  function clearErrors(form) {
    form.querySelectorAll(".field-error").forEach(function (node) {
      node.textContent = "";
      node.classList.add("d-none");
    });
  }

  function renderItems(container, items) {
    container.innerHTML = "";
    items.forEach(function (item) {
      var div = document.createElement("div");
      div.textContent = escapeHtml(item.name);
      container.appendChild(div);
    });
  }

  // 5. FUNÇÕES DE EVENT BINDING ("init" ou "bind" prefix)
  function bindFormSubmission(form) {
    if (!form) return;
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      // Handle submission
    });
  }

  function initializePhotoManager() {
    var input = document.getElementById("photo-input");
    if (!input) return;
    input.addEventListener("change", function () {
      // Handle photo change
    });
  }

  // 6. FUNÇÃO PRINCIPAL (orchestration e initialization)
  function init() {
    var form = resolveForm("my-form");
    if (!form) return;

    bindFormSubmission(form);
    initializePhotoManager();
  }

  // 7. API PÚBLICA (window.*)
  window.MyModule = {
    init: init,
    escapeHtml: escapeHtml  // Se necessário exportar
  };

  // 8. INITIALIZATION TRIGGER
  document.addEventListener("DOMContentLoaded", init);
})();
```

---

### 2.3 Padrões de Segurança (XSS Prevention)

#### ❌ NUNCA use `innerHTML` com valores concatenados:
```javascript
// PERIGOSO - XSS vulnerability
container.innerHTML = '<div>' + userInput + '</div>';  // ❌ NÃO FAZER ISTO

// PERIGOSO - XSS vulnerability (mesmo com escaping manual)
var div = document.createElement("div");
div.innerHTML = '<span>Latitude: ' + latitude + '</span>';  // ❌ Ainda arriscado
```

#### ✅ USE `textContent` para valores, `createElement` para estrutura:
```javascript
// SEGURO - textContent nunca interpreta HTML
var div = document.createElement("div");
div.className = "detail-box";
div.textContent = "Latitude: " + latitude + " | Longitude: " + longitude;
container.appendChild(div);

// SEGURO - HTML escaping para labels estáticos
var label = document.createElement("label");
label.textContent = escapeHtml(userInput);  // Seguro mesmo sem escaping (textContent não interpreta)
element.appendChild(label);
```

#### Função Helper para escaping (se necessário):
```javascript
function escapeHtml(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
```

---

## 3. Padrões Comuns Reutilizáveis

### 3.1 Async Form Submission

**Use o core `window.SiopAsyncForm` ou criar wrapper local**:

```javascript
(function () {
  function submitForm(form) {
    if (!form || typeof window.SigoCsrf === "undefined") return;

    var submitButton = form.querySelector('[type="submit"]');
    var originalText = submitButton ? submitButton.textContent : "";

    if (submitButton) {
      submitButton.disabled = true;
      submitButton.textContent = "Salvando...";
    }

    window.SigoCsrf.fetch(form.dataset.apiUrl, {
      method: "POST",
      body: new FormData(form)
    })
      .then(function (response) {
        return response.json().then(function (payload) {
          return { response: response, payload: payload };
        });
      })
      .then(function (result) {
        if (result.response.ok && result.payload.ok) {
          window.location.href = result.payload.data.redirect_url || "/";
          return;
        }
        // Handle errors
      })
      .catch(function () {
        alert("Erro ao enviar formulário.");
      })
      .finally(function () {
        if (submitButton) {
          submitButton.disabled = false;
          submitButton.textContent = originalText;
        }
      });
  }

  function initForm() {
    var form = document.getElementById("my-form");
    if (!form) return;
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      submitForm(form);
    });
  }

  document.addEventListener("DOMContentLoaded", initForm);
})();
```

### 3.2 Geolocation Capture

**Use o core `window.SesmtGeolocation.initCapture()`** (SESMT):

```javascript
window.SesmtGeolocation.initCapture({
  latitudeId: "latitude-input",
  longitudeId: "longitude-input",
  containerId: "geo-display",
  emptyNodeId: "geo-empty",
  onChange: function () {
    // Callback on successful capture
  }
});
```

### 3.3 Photo/File Management

**Use o core `window.SesmtPhotoManager.init()`** (SESMT):

```javascript
window.SesmtPhotoManager.init({
  inputId: "photo-input",
  statusId: "photo-status",
  listId: "photo-list",
  emptyId: "photo-empty",
  onChange: function () {
    // Callback on file change
  }
});
```

### 3.4 Export/Download Handler

**Use o core `window.SesmtExportHandler.bind()`** (SESMT):

```javascript
window.SesmtExportHandler.bind(
  "export-form-id",
  "/api/export/endpoint/",
  "default-filename.xlsx"
);
```

---

## 4. Regras de Estilo de Código

### 4.1 Nomes e Convenções

| Item | Padrão | Exemplo |
|------|--------|---------|
| **Variáveis/Funções** | `camelCase` | `submitButton`, `initPhotoManager()` |
| **Constantes** | `UPPER_SNAKE_CASE` | `MAX_FILE_SIZE`, `VALID_TYPES` |
| **Classes CSS** | `kebab-case` com prefix `js-` para seletores | `.js-toggle-field`, `.field-error` |
| **IDs HTML** | `snake_case` | `photo-input`, `geo-display` |
| **Prefixos** | Init/bind funções: `init*()`, `bind*()` | `initForm()`, `bindSubmission()` |

### 4.2 Verificações Nulas

```javascript
// ✓ BOM - early return pattern
function process(element) {
  if (!element) return;
  // Continue with element

  var child = element.querySelector(".child");
  if (!child) return;
  // Continue with child
}

// ✗ EVITAR - nested deep
function process(element) {
  if (element) {
    if (element.querySelector) {
      var child = element.querySelector(".child");
      if (child) {
        // ...
      }
    }
  }
}
```

### 4.3 Event Listeners

```javascript
// ✓ BOM - scoped queries
form.querySelector('[type="submit"]').addEventListener("click", function () { });
form.querySelectorAll(".field-error").forEach(function (node) { });

// ✓ BOM - event delegation com closest()
document.addEventListener("click", function (event) {
  var button = event.target.closest("[data-action]");
  if (button) {
    // Handle click
  }
});

// ✗ EVITAR - global queries quando possível
document.getElementById("my-button").addEventListener("click", function () { });
```

---

## 5. Checklist de Criação de Novo Arquivo JavaScript

Ao criar um novo arquivo `<modulo>-<feature>-<tipo>.js`:

- [ ] **Nome do arquivo** segue `<modulo>-<feature>-<tipo>.js` (ex: `siop-efetivo-form.js`)
- [ ] **Estrutura IIFE** com scope isolado `(function () { ... })();`
- [ ] **Funções organizadas** em ordem: constants → helpers → DOM queries → DOM manipulation → event binding → init → public API
- [ ] **Sem `innerHTML`** com valores concatenados; usar `createElement` + `textContent`
- [ ] **Verificações nulas** em todas as seleções do DOM (`if (!element) return;`)
- [ ] **Nomes claros** em `camelCase` para variáveis/funções
- [ ] **Comments** para funções complexas, especialmente public API
- [ ] **DOMContentLoaded** ou condicional inline para trigger
- [ ] **Sem código global** (tudo dentro da IIFE)
- [ ] **Módulos reutilizáveis** extraídos para `/core/` se >100 linhas
- [ ] **Documentação** em bloco de comentário no topo do arquivo

### Template Inicial

```javascript
/**
 * <Modulo> <Feature> - <Descripção curta>
 * Handles: form submission, photo management, etc.
 * Dependencies: window.SigoCsrf, window.SesmtPhotoManager (if applicable)
 */
(function () {
  // CONSTANTS
  var FORM_ID = "my-form";
  var API_URL = "/api/my-endpoint/";

  // HELPERS
  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // DOM QUERIES
  function getForm() {
    return document.getElementById(FORM_ID);
  }

  // DOM MANIPULATION
  function clearForm(form) {
    if (!form) return;
    form.reset();
  }

  // EVENT BINDING
  function bindFormSubmission(form) {
    if (!form) return;
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      // Handle submission
    });
  }

  // INITIALIZATION
  function init() {
    var form = getForm();
    if (!form) return;
    bindFormSubmission(form);
  }

  // PUBLIC API
  window.MyModule = {
    init: init
  };

  // TRIGGER
  document.addEventListener("DOMContentLoaded", init);
})();
```

---

## 6. Migração de Código Legado (SESMT)

Para módulos legados como SESMT que tinham código duplicado:

### **Antes (Duplicado)**
```javascript
// atendimento-form.js (~787 lines)
// - Photo management code (100+ lines)
// - Geolocation code (80+ lines)
// - Export code (60+ lines)

// flora-form.js (~480 lines)
// - Photo management code (DUPLICATED)
// - Geolocation code (DUPLICATED)
// - Export code (DUPLICATED)
```

### **Depois (Modular)**
```javascript
// CORES (reutilizáveis)
// core/photo-manager.js       (260 lines)
// core/geolocation.js         (153 lines)
// core/async-export.js        (77 lines)

// FEATURES (usando cores)
// atendimento-form.js         (508 lines → -279 lines)
// flora-form.js               (167 lines → -313 lines)
// himenopteros-form.js        (153 lines → -297 lines)
// manejo-form.js              (222 lines → -318 lines)

// EXPORT (usando cores)
// atendimento-export.js       (9 lines → -59 lines)
// flora-export.js             (9 lines → -59 lines)
// himenopteros-export.js      (9 lines → -59 lines)
// manejo-export.js            (9 lines → -59 lines)

// TOTAL: ~3,500 lines → ~1,500 lines (57% reduction)
```

### Estratégia de Refatoração

1. **Identifique código duplicado** entre features
2. **Extraia para `/core/<funcionalidade>.js`** com public API em `window.*`
3. **Atualize features** para usar `window.SesmtFeatureName.init(config)`
4. **Remova funções originais** (não deixe duplicatas)
5. **Adicione cores nos templates** ANTES das features
6. **Teste** com `python manage.py check`

---

## 7. Carregamento de Scripts nas Templates Django

### Ordem Crítica

```html
<!-- 1. Core modules first -->
<script src="{% static 'sigo/assets/js/sesmt/core/photo-manager.js' %}"></script>
<script src="{% static 'sigo/assets/js/sesmt/core/geolocation.js' %}"></script>
<script src="{% static 'sigo/assets/js/sesmt/core/async-export.js' %}"></script>

<!-- 2. Then feature scripts (que dependem dos cores) -->
<script src="{% static 'sigo/assets/js/sesmt/atendimento-form.js' %}"></script>
<script src="{% static 'sigo/assets/js/sesmt/atendimento-export.js' %}"></script>

<!-- 3. Repeat for other modules -->
<script src="{% static 'sigo/assets/js/sesmt/flora-form.js' %}"></script>
<script src="{% static 'sigo/assets/js/sesmt/flora-export.js' %}"></script>
```

⚠️ **Importante**: Cores devem ser carregados **antes** de qualquer arquivo que os use.

---

## 8. Referências

- **Exemplar SIOP**: `/static/sigo/assets/js/siop/` - Código modular de referência
- **SESMT (refatorado)**: `/static/sigo/assets/js/sesmt/` - Aplicação prática do padrão
- **Análise detalhada**: `/docs/JAVASCRIPT_ANALYSIS.md`
- **Padrão de módulos**: Ver `/docs/padrao_create_module_project.md` seção 4

---

**Versão**: 1.0  
**Atualizado**: 16 de abril de 2026  
**Responsável**: Arquitetura de Código
