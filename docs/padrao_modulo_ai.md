# Padrão Oficial para Novos Módulos (Humano e AI)

Este documento define o padrão arquitetural oficial para criação de novos módulos no projeto.

Objetivo:

- manter consistência entre áreas
- reduzir acoplamento
- facilitar manutenção e testes
- permitir que qualquer AI gere código no mesmo estilo do projeto

## 1. Convenções gerais

- Framework: Django
- Idioma de código e commits: português técnico
- Fluxo web padrão por área:
  - `index`
  - `list`
  - `new`
  - `edit`
  - `view`
  - `export`
  - `export_view_pdf`
- Fluxo API padrão por área:
  - `api_<area>` (coleção)
  - `api_<area>_detail` (detalhe)
  - `api_<area>_export` (exportação)
  - catálogos auxiliares quando necessário (`api_locais`, `api_especies`, etc.)

## 2. Estrutura de pastas obrigatória

Para cada nova área dentro de um app de domínio (exemplo: `siop/nova_area` ou `sesmt/nova_area`):

- `__init__.py`
- `views.py`
- `services.py`
- `query.py`
- `serializers.py`
- `support.py`
- `common.py` (opcional, mas recomendado quando houver utilitários reutilizáveis)

## 3. Responsabilidade de cada arquivo

### 3.1 `views.py`

Deve conter apenas camada HTTP:

- leitura de `request`
- escolha de template
- retorno de `render`, `redirect`, `api_success`, `api_error`
- paginação de tela quando necessário

Não deve concentrar regra de negócio pesada.

### 3.2 `services.py`

Regras de negócio e orquestração:

- criação e edição de registros
- validações de domínio complementares
- publicação de notificações
- persistência de anexos/fotos/assinaturas/geolocalização

### 3.3 `query.py`

Consultas e filtros reutilizáveis:

- queryset base
- aplicação de filtros de busca
- filtros de período
- ordenação e paginação
- dados de dashboard

### 3.4 `serializers.py`

Padronização de payloads para API:

- serialização de listagem
- serialização de detalhe
- payload de evidências e auditoria

### 3.5 `support.py` e `common.py`

Funções pequenas e reutilizáveis:

- normalização de strings
- mapeamentos de catálogo
- formatadores e helpers leves

## 4. Rotas e imports

No arquivo `urls.py` do app:

- importar `home` e `notifications_list` das views centrais do app (`core_views.py` ou equivalente)
- importar rotas de cada área diretamente da respectiva pasta (`from .nova_area.views import ...`)
- evitar depender de uma fachada única para roteamento interno

Fachada de compatibilidade (`views.py` no root do app) pode existir para não quebrar legado, mas não deve ser obrigatória para novas rotas.

## 5. Templates

Estrutura de templates por área:

- `<app>/templates/<app>/<area>/base.html`
- `<app>/templates/<app>/<area>/index.html`
- `<app>/templates/<app>/<area>/list.html`
- `<app>/templates/<app>/<area>/new.html`
- `<app>/templates/<app>/<area>/edit.html`
- `<app>/templates/<app>/<area>/view.html`
- `<app>/templates/<app>/<area>/export.html`

Listagens devem seguir padrão `API + fetch` já adotado no projeto.

## 6. JavaScript por área

Criar arquivos em `static/sigo/assets/js/<app>/`:

- `<area>-form.js`
- `<area>-view.js`
- `<area>-export.js`

Regras:

- evitar sintaxe não suportada pelos scanners de segurança, quando houver dúvida
- manter escapes e sanitização em renderização HTML dinâmica
- usar rotas da API para listagem e detalhe

## 7. Models e migrations

Para novos modelos:

- herdar da base padrão usada no projeto quando aplicável
- validar domínio em `clean()` e chamar `full_clean()` no fluxo de serviço quando necessário
- usar `db_index` e índices compostos com critério (baseado em filtros reais)
- gerar migrations pequenas e legíveis

## 8. Notificações e auditoria

Toda área nova deve prever:

- notificação de criação
- notificação de atualização relevante
- campos de auditoria (`criado_por`, `modificado_por`, datas)
- serialização de auditoria no detalhe da API

## 9. Exportações

Padrão mínimo:

- exportação CSV
- exportação XLSX
- PDF por registro (`export_view_pdf`)

Reaproveitar utilitários compartilhados já existentes no projeto.

## 10. Testes mínimos obrigatórios

Para cada área nova:

- teste de criação
- teste de edição
- teste de listagem com filtro principal
- teste de API de detalhe
- teste de exportação (pelo menos um formato)

## 11. Checklist de entrega para AI

Antes de concluir um módulo novo, a AI deve garantir:

- estrutura de pastas completa conforme seção 2
- rotas web e API registradas
- templates principais criados
- scripts JS principais criados
- serializers de listagem e detalhe implementados
- serviços de criação/edição implementados
- filtros em `query.py` implementados
- documentação da área atualizada em `docs/`
- testes mínimos adicionados

## 12. Prompt recomendado para AI (copiar e usar)

"Crie uma nova área no projeto Django seguindo estritamente o padrão arquitetural de `docs/padrao_modulo_ai.md`. Gere estrutura completa com models (se necessário), services, query, serializers, support, views, urls, templates, scripts JS, exportações e testes mínimos. Use nomenclatura e fluxo isonômicos às áreas do SIOP/SESMT já existentes e mantenha compatibilidade com o padrão API + fetch."