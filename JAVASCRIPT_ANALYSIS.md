# JavaScript Assets Directory Analysis

## 1. Directory Structure and Organization

### Overall Layout
```
/static/sigo/assets/js/
├── core/                    # External dependencies
│   ├── bootstrap.min.js
│   ├── jquery-3.7.1.min.js
│   └── popper.min.js
├── plugin/                  # Third-party plugins
│   ├── chart.js/
│   ├── jquery-scrollbar/
│   └── webfont/
├── sigo/                    # Core framework & shared UI (8 files)
│   ├── csrf.js
│   ├── dashboard-charts.js
│   ├── login.js
│   ├── sigo-app.js
│   ├── sigo-fonts.js
│   ├── sigo.min.js
│   ├── sigo-theme-init.js
│   └── siop-dashboard.js
├── sesmt/                   # SESMT module (12 files)
│   ├── atendimento-{form,view,export}.js
│   ├── flora-{form,view,export}.js
│   ├── himenopteros-{form,view,export}.js
│   └── manejo-{form,view,export}.js
└── siop/                    # SIOP module (11 files)
    ├── async-form.js
    ├── async-list.js
    ├── acesso-colaboradores-form.js
    ├── acesso-terceiros-form.js
    ├── achados-perdidos-form.js
    ├── controle-ativos-form.js
    ├── controle-chaves-form.js
    ├── crachas-provisorios-form.js
    ├── efetivo-form.js
    ├── liberacao-acesso-form.js
    └── ocorrencias-form.js
```

### Statistics
- **Total JavaScript files**: 37
- **Custom files** (excluding core & plugins): 31
- **Core dependencies**: 3 files
- **Module distribution**:
  - SIGO (Core/UI): 8 files
  - SESMT (Environmental): 12 files
  - SIOP (Security/Access): 11 files

---

## 2. File Naming Conventions

### Pattern: `<module>-<page-type>.js`

**Naming structure** follows a consistent pattern:
- **Module prefix**: `sesmt/`, `siop/`, `sigo/`
- **Feature/Model name**: descriptive kebab-case (e.g., `atendimento`, `flora`, `himenopteros`)
- **Page type suffix**: specific action or purpose

### Page Type Categories

#### **Form Files** (`*-form.js`)
- Handle form initialization and submission
- Catalog synchronization and field dependencies
- File upload management
- Examples:
  - `sesmt/atendimento-form.js`
  - `siop/acesso-colaboradores-form.js`
  - `siop/async-form.js` (reusable form handler)

#### **View Files** (`*-view.js`)
- Display detail pages with formatted data
- HTML rendering for records
- Examples:
  - `sesmt/atendimento-view.js`
  - `sesmt/flora-view.js`

#### **Export Files** (`*-export.js`)
- Handle CSV/Excel export functionality
- File download management
- Examples:
  - `sesmt/atendimento-export.js`
  - `sesmt/flora-export.js`

#### **Utility/Support Files**
- `csrf.js` - CSRF token management
- `async-form.js` - Reusable async form handler
- `async-list.js` - Reusable list pagination & filtering
- `dashboard-charts.js` - Chart rendering utilities
- `sigo-theme-init.js` - Theme initialization
- `sigo-app.js` - Main application setup

---

## 3. Code Patterns and Structure

### 3.1 Module Pattern (Immediately Invoked Function Expression - IIFE)

**All files use the IIFE pattern** to create isolated scopes and prevent global namespace pollution:

```javascript
(function () {
  // Private functions and state
  function privateHelper() { }
  
  // Public API (if needed)
  window.SigoCsrf = {
    getCookie: getCookie,
    fetch: csrfFetch,
  };
})();
```

**Advantages**:
- Encapsulation: prevents global namespace pollution
- Privacy: variables/functions not exposed globally
- Isolation: each module has its own scope

### 3.2 Function Organization

Typical function structure in module files:

```
1. Helper/Utility functions (non-DOM specific)
   - Data processing, formatting, validation
   - Examples: escapeHtml(), buildOptions(), parseJsonScript()

2. DOM Query & Selection functions
   - Finding elements, resolving targets
   - Examples: getFeedbackBox(), resolveErrorTarget()

3. DOM Manipulation functions
   - Modifying DOM state (classes, attributes, content)
   - Examples: showFormFeedback(), buildOptions()

4. Event Binding functions
   - Setting up event listeners
   - Named with "init" or "bind" prefix
   - Examples: bindSidebarHoverBehavior(), syncLocais()

5. Initialization function
   - Main entry point that sets everything up
   - Called at document load or via DOMContentLoaded
```

### 3.3 Common Helper Function Patterns

#### **HTML Escaping**
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

#### **DOM Element Existence Checks**
```javascript
if (!element) return;  // Early exit pattern used consistently
```

#### **Safe Type Conversions**
```javascript
String(value == null ? "" : value).trim()
Array.isArray(messages) ? messages.join(" ") : String(messages || "")
```

#### **Element Selection with Fallback**
```javascript
document.getElementById(id) || document.querySelector('[name="' + name + '"]')
```

### 3.4 Document Ready Patterns

**Pattern 1: DOMContentLoaded Event**
```javascript
document.addEventListener("DOMContentLoaded", initFunction);
```

**Pattern 2: Inline Conditional Check**
```javascript
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bindSidebarHoverBehavior);
} else {
  bindSidebarHoverBehavior();
}
```

**Pattern 3: Inline Execution (for critical setup)**
```javascript
(function () {
  var savedTheme = localStorage.getItem("sigo-theme");
  root.setAttribute("data-sigo-theme", initialTheme);
})();  // Executes immediately
```

### 3.5 Event Handling Patterns

#### **Direct Event Listeners**
```javascript
element.addEventListener("click", function(event) {
  event.preventDefault();
  // Handle event
});
```

#### **Event Delegation (using querySelectorAll + forEach)**
```javascript
document.querySelectorAll(".js-toggle-field").forEach(function (node) {
  // Setup for each matching element
});
```

#### **Event Target Resolution**
```javascript
var target = event.target.closest(".selector");
if (target && target.dataset.triggerFile) {
  var input = document.getElementById(target.dataset.triggerFile);
}
```

---

## 4. Common Patterns Used Across Files

### 4.1 Form Handling Pattern

**Standard async form submission flow**:

1. **Form Selection & Validation**
   ```javascript
   var form = document.getElementById("form-id");
   if (!form) return;
   ```

2. **Request Target Resolution**
   ```javascript
   var method = form.dataset.apiMethod || form.getAttribute("method") || "POST";
   var url = form.dataset.apiUrl || form.getAttribute("action");
   ```

3. **Error Clearing**
   ```javascript
   clearFieldErrors(form);
   hideFormFeedback(form);
   ```

4. **Form Submission**
   ```javascript
   form.addEventListener("submit", function(event) {
     event.preventDefault();
     // Disable button, submit via fetch
   });
   ```

5. **Response Handling**
   ```javascript
   .then(response => response.json())
   .then(payload => {
     if (payload.ok) {
       // Redirect or show success
     } else {
       // Render errors
     }
   })
   .catch(err => showFormFeedback(form, "Error", "danger"));
   ```

### 4.2 Catalog/Select Field Synchronization

**Cascading select pattern** (used in multiple form files):

```javascript
function syncLocais(areaField, localField) {
  var locaisUrl = areaField.dataset.locaisUrl;
  
  areaField.addEventListener("change", function() {
    requestCatalog(locaisUrl, "area", areaField.value)
      .then(payload => {
        var locais = (((payload || {}).data || {}).locais) || [];
        buildOptions(localField, locais, "Selecione");
      });
  });
}
```

**Key features**:
- Uses `data-*` attributes to pass configuration
- Handles API responses with nested object destructuring
- Rebuilds select options dynamically
- Preserves user's previous selection when possible

### 4.3 File Upload Management

**Photo/File upload pattern**:

```javascript
function initPhotoManager(config) {
  var input = document.getElementById(config.inputId);
  var listNode = document.getElementById(config.listId);
  
  input.addEventListener("change", function() {
    var files = Array.from(input.files || []);
    // Process files
  });
}
```

**Features**:
- Uses configuration object for dependency injection
- Maintains list of selected files
- Allows removal of existing and new files
- Creates hidden input fields for deletions

### 4.4 Pagination Pattern

**Async list pagination**:

```javascript
function buildPagination(total, pageSize, page) {
  var totalPages = Math.ceil(total / pageSize);
  var hasPrevious = page > 1;
  var hasNext = page < totalPages;
  
  return '<ul class="pagination">' + 
    renderControl("Primeira", 1, !hasPrevious) +
    renderControl("Anterior", page - 1, !hasPrevious) +
    // ...
    '</ul>';
}
```

**Features**:
- Calculates pagination state
- Renders HTML string for pagination controls
- Handles first/last/previous/next navigation
- Displays total records and current page

### 4.5 Export/Download Pattern

**File download implementation**:

```javascript
.then(response => response.blob())
.then(blob => {
  var url = URL.createObjectURL(blob);
  var link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
});
```

**Features**:
- Converts API response to Blob
- Creates temporary download link
- Extracts filename from Content-Disposition header
- Cleans up object URLs to prevent memory leaks

### 4.6 Theme Management Pattern

**System theme detection and persistence**:

```javascript
var savedTheme = localStorage.getItem("sigo-theme");
var mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
var initialTheme = savedTheme || (mediaQuery.matches ? "dark" : "light");

root.setAttribute("data-sigo-theme", initialTheme);
root.setAttribute("data-bs-theme", initialTheme);

mediaQuery.addEventListener("change", function(event) {
  applyTheme(event.matches ? "dark" : "light");
});
```

**Features**:
- Respects user preference
- Falls back to system preference
- Uses localStorage persistence
- Integrates with Bootstrap theme system

### 4.7 CSRF Protection Pattern

**Token acquisition and header injection**:

```javascript
function getCsrfToken() {
  return getCookie('csrftoken');
}

function buildCsrfHeaders(extraHeaders) {
  const headers = Object.assign({}, extraHeaders || {});
  const token = getCsrfToken();
  if (token && !headers['X-CSRFToken']) {
    headers['X-CSRFToken'] = token;
  }
  headers['X-Requested-With'] = 'XMLHttpRequest';
  return headers;
}

window.SigoCsrf = {
  fetch: csrfFetch,  // Wrapper that injects CSRF token
};
```

**Features**:
- Centralized CSRF token management
- Prevents duplicate headers
- Marks requests as XMLHttpRequest
- Automatically includes credentials

---

## 5. Dependencies and Module Relationships

### 5.1 External Dependencies

**Core Libraries**:
- **jQuery 3.7.1** (`core/jquery-3.7.1.min.js`) - DOM manipulation
- **Bootstrap 5** (`core/bootstrap.min.js`) - UI components & styling
- **Popper.js** (`core/popper.min.js`) - Positioning library for Bootstrap

**Plugins**:
- **Chart.js** (`plugin/chart.js/chart.min.js`) - Chart rendering
- **jQuery Scrollbar** (`plugin/jquery-scrollbar/jquery.scrollbar.min.js`) - Custom scrollbars
- **WebFont Loader** (`plugin/webfont/webfont.min.js`) - Font loading

### 5.2 Internal Module Dependencies

#### **Core Module** (`sigo/`)
- **sigo-theme-init.js**: Standalone initialization
  - Used: On page load (before other scripts)
  - Purpose: Early theme setup to prevent FOUC

- **csrf.js**: Utility provider
  - Used by: All form submission scripts
  - Provides: `window.SigoCsrf` global object
  - Features: Cookie parsing, header building, fetch wrapper

- **sigo-app.js**: Main orchestrator
  - Sets up: Theme toggle, sidebar hover behavior
  - Depends on: DOM elements with specific classes
  - Scope: Page-wide UI interactions

- **dashboard-charts.js**: Chart rendering utility
  - Used by: Dashboard pages
  - Depends on: Chart.js library
  - Feature: Theme-aware chart configuration

- **login.js**: Login page specific
  - Used by: Login template
  - Feature: Password visibility toggle

- **siop-dashboard.js**: SIOP dashboard
  - Used by: SIOP dashboard template

- **sigo-fonts.js**: Font initialization
- **sigo.min.js**: Minified aggregate or compiled bundle

#### **SESMT Module** (`sesmt/`)
- **atendimento-form.js**, **flora-form.js**, **himenopteros-form.js**, **manejo-form.js**
  - Pattern: Module-specific form handlers
  - Each implements: Catalog sync, file uploads, field dependencies
  - Reused patterns: `requestCatalog()`, `buildOptions()`, `syncAreaLocais()`

- **atendimento-view.js**, **flora-view.js**, **himenopteros-view.js**, **manejo-view.js**
  - Pattern: Detail view renderers
  - Features: HTML string construction, data formatting
  - Shared utilities: `escapeHtml()`, `field()`, `section()`, `boolLabel()`

- **atendimento-export.js**, **flora-export.js**, **himenopteros-export.js**, **manejo-export.js**
  - Pattern: Export/download handlers
  - Shared implementation: File download via blob + blob URL
  - Features: Disable button during export, error handling

#### **SIOP Module** (`siop/`)
- **async-form.js**: Reusable async form handler
  - Used by: All SIOP form files
  - Purpose: Centralized form submission logic
  - Features: CSRF integration, error rendering, redirect handling
  - Binding: Called explicitly from individual form handlers

- **async-list.js**: Reusable pagination handler
  - Used by: List/search pages in SIOP
  - Purpose: Pagination + filtering
  - Features: Query string building, HTML generation, page navigation

- **acesso-colaboradores-form.js** through **ocorrencias-form.js**: Form handlers
  - Pattern: Each calls/uses `async-form.js`
  - Specific logic: Module-specific catalog sync, field setup
  - Each file: ~40-80 lines, focused on initialization

### 5.3 Dependency Graph

```
External Libraries (Core & Plugins)
│
├── csrf.js ──────────────────────────┐
│                                      │
├── sigo-app.js (standalone)           │
├── sigo-theme-init.js (earliest)      │
├── login.js (standalone)              │
└── dashboard-charts.js ───────┐       │
                               │       │
    SESMT Module               │       │
    ├── *-form.js ─────────────┼───────┤──> All Forms
    ├── *-view.js             │       │
    └── *-export.js ──────────┘       │
                                       │
    SIOP Module                        │
    ├── async-form.js ─────────────────┤──────┐
    ├── async-list.js                  │      │
    └── [specific-form.js] ────────────┘      │
                                              │
    Usage Flow:
    1. sigo-theme-init.js (immediate)
    2. csrf.js (loaded early)
    3. sigo-app.js (app initialization)
    4. async-form.js (available for forms)
    5. Individual form/view/export handlers
```

### 5.4 Data Flow Patterns

#### **API Communication**
All modules follow similar data flow:

```
User Interaction (form submit, button click)
  ↓
DOM Event Handler
  ↓
Fetch API Request (with CSRF headers)
  ↓
JSON Response Parsing
  ↓
Success: Redirect or Update DOM
Failure: Render Validation Errors
```

#### **Select Field Synchronization**
```
Area Select Change
  ↓
Fetch Catalog API (area parameter)
  ↓
Parse Response (nested object destructuring)
  ↓
Rebuild Local Select Options
  ↓
Restore Previous Value if Valid
```

#### **Theme Management**
```
Page Load (sigo-theme-init.js)
  ↓
Check: localStorage → System preference
  ↓
Set data-sigo-theme and data-bs-theme
  ↓
Listen to System Changes
```

---

## 6. Code Quality Observations

### 6.1 Strengths

1. **Consistency**: Uniform patterns across all modules
2. **Encapsulation**: All code wrapped in IIFE for scope isolation
3. **Error Handling**: Comprehensive try-catch and null checks
4. **HTML Escaping**: All user data escaped to prevent XSS
5. **CSRF Protection**: Centralized and consistent token handling
6. **Responsive Design**: Media queries for mobile/desktop differentiation
7. **Accessibility**: ARIA labels and semantic HTML
8. **Performance**: Event delegation where appropriate
9. **Memory Management**: Cleanup of object URLs and event listeners

### 6.2 Patterns for Maintainability

1. **Naming**: Clear, descriptive function names
2. **Documentation**: Code is self-documenting with clear intent
3. **Modularity**: Each file has single responsibility
4. **DRY Principle**: Shared utilities extracted to async-form.js and async-list.js
5. **Configuration**: Uses data-* attributes for configuration injection

### 6.3 Notes on Technology Choices

- **No Front-End Framework**: Uses vanilla JavaScript + jQuery
- **ES5 Compatible**: Uses `var`, function expressions, no arrow functions
- **jQuery Selective**: jQuery primarily for Bootstrap integration
- **Fetch API**: Modern AJAX without jQuery.ajax()
- **Bootstrap 5**: Full integration for UI/components
- **LocalStorage**: For persistent client-side state (theme)

---

## 7. Summary of Key Conventions

### Must-Follow Patterns

1. **Module Encapsulation**: Always wrap in IIFE
   ```javascript
   (function() { /* code */ })();
   ```

2. **Null/Undefined Checks**: Always check before DOM manipulation
   ```javascript
   if (!element) return;
   ```

3. **HTML Escaping**: Always escape user-provided content
   ```javascript
   escapeHtml(userValue)
   ```

4. **CSRF Headers**: Always use `window.SigoCsrf.fetch()` for authenticated requests
   ```javascript
   window.SigoCsrf.fetch(url, { method: "POST", body: data })
   ```

5. **Event Prevention**: Always call `event.preventDefault()` on form submits
   ```javascript
   form.addEventListener("submit", function(e) { e.preventDefault(); });
   ```

6. **Error Handling**: Always include `.catch()` for fetch calls
   ```javascript
   fetch().then().catch(function() { /* error handling */ });
   ```

7. **Configuration via Data Attributes**: Use `data-*` for HTML-to-JS configuration
   ```html
   <form data-api-url="/api/endpoint" data-api-method="POST">
   ```

### File Structure Template

```javascript
(function() {
  // 1. Configuration extraction
  var form = document.getElementById("form-id");
  if (!form) return;
  var apiUrl = form.dataset.apiUrl;
  
  // 2. Helper functions
  function helperFunction() { }
  
  // 3. DOM manipulation functions
  function updateDOM() { }
  
  // 4. Event binding
  function bindEvents() {
    form.addEventListener("submit", function(e) {
      e.preventDefault();
      // submit logic
    });
  }
  
  // 5. Initialization
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindEvents);
  } else {
    bindEvents();
  }
  
  // 6. Public API (if needed)
  window.ModuleName = { publicFunction: helperFunction };
})();
```

---

## 8. Recommended Reading Order

1. **sigo-theme-init.js** - Simplest example
2. **csrf.js** - Utility/provider pattern
3. **login.js** - Simple single-feature handler
4. **async-form.js** - Complex form handling pattern
5. **async-list.js** - Pagination pattern
6. **sesmt/flora-form.js** - Real-world form with catalog sync
7. **sigo-app.js** - Complex multi-feature module

