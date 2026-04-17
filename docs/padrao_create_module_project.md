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
- Base de referência para isonomia: SIOP
- Convenções de nome:
  - pasta da área: `snake_case` (`acesso_colaboradores`, `controle_chaves`)
  - segmento de URL da área: `kebab-case` (`acesso-colaboradores`, `controle-chaves`)
  - nomes de views e rotas: `snake_case`
  - arquivos JavaScript por área: `kebab-case`
  - diretório de templates da área: `snake_case`
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

Arquivos raiz esperados no app de domínio:

- `dashboard_views.py` para `home` e `notifications_list`
- `download_views.py` quando o app expuser downloads centralizados por `pk` direto (`anexo_download`, `foto_download`, `assinatura_download`)
- `views.py` apenas como fachada de compatibilidade, nunca como ponto obrigatório de roteamento novo
- `urls.py` importando diretamente de `dashboard_views.py` e de cada `<area>.views`

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

- importar `home` e `notifications_list` de `dashboard_views.py`
- importar rotas de cada área diretamente da respectiva pasta (`from .nova_area.views import ...`)
- evitar depender de uma fachada única para roteamento interno

Fachada de compatibilidade (`views.py` no root do app) pode existir para não quebrar legado, mas não deve ser obrigatória para novas rotas.

### 4.1 Nome obrigatório das views por área

Mesmo que a implementação ainda esteja vazia, a área nova já deve nascer com estas funções declaradas em `<app>/<area>/views.py`:

- `<area>_index`
- `<area>_list`
- `<area>_new`
- `<area>_edit`
- `<area>_view`
- `<area>_export`
- `<area>_export_view_pdf`
- `api_<area>`
- `api_<area>_detail`
- `api_<area>_export`

Catálogos auxiliares devem seguir o mesmo padrão de nome:

- `<area>_api_locais`
- `<area>_api_especies`
- `api_<area>_chegada`
- `api_<area>_<acao_especifica>`

Regra: se a área tiver fotos, assinaturas ou anexos próprios com validação pelo registro pai, declarar também:

- `<area>_foto_view`
- `<area>_assinatura_view`
- `<area>_anexo_view`

### 4.2 Nome obrigatório das rotas

Seguir o padrão do SIOP:

- path da área em `kebab-case`
- nome da rota em `snake_case`

Exemplo para uma área `controle_visitantes`:

- `path('controle-visitantes/', controle_visitantes_index, name='controle_visitantes_index')`
- `path('controle-visitantes/lista/', controle_visitantes_list, name='controle_visitantes_list')`
- `path('controle-visitantes/novo/', controle_visitantes_new, name='controle_visitantes_new')`
- `path('controle-visitantes/exportar/', controle_visitantes_export, name='controle_visitantes_export')`
- `path('controle-visitantes/<int:pk>/export/pdf-view/', controle_visitantes_export_view_pdf, name='controle_visitantes_export_view_pdf')`
- `path('controle-visitantes/<int:pk>/', controle_visitantes_view, name='controle_visitantes_view')`
- `path('controle-visitantes/<int:pk>/editar/', controle_visitantes_edit, name='controle_visitantes_edit')`
- `path('api/controle-visitantes/', api_controle_visitantes, name='api_controle_visitantes')`
- `path('api/controle-visitantes/export/', api_controle_visitantes_export, name='api_controle_visitantes_export')`
- `path('api/controle-visitantes/<int:pk>/', api_controle_visitantes_detail, name='api_controle_visitantes_detail')`

Se houver downloads centralizados por `pk` direto no app:

- `path('anexos/<int:pk>/download/', anexo_download, name='anexo_download')`
- `path('fotos/<int:pk>/download/', foto_download, name='foto_download')`
- `path('assinaturas/<int:pk>/download/', assinatura_download, name='assinatura_download')`

## 5. Templates

Estrutura de templates por área:

- `<app>/templates/<app>/base.html`
- `<app>/templates/<app>/index.html`
- `<app>/templates/<app>/notifications.html`
- `<app>/templates/<app>/<area>/base.html`
- `<app>/templates/<app>/<area>/index.html`
- `<app>/templates/<app>/<area>/list.html`
- `<app>/templates/<app>/<area>/new.html`
- `<app>/templates/<app>/<area>/edit.html`
- `<app>/templates/<app>/<area>/view.html`
- `<app>/templates/<app>/<area>/export.html`

### 5.1 Regra de nomenclatura dos templates

- diretório da área sempre em `snake_case`
- arquivos com nome fixo e previsível
- não criar nomes alternativos como `create.html`, `detail.html`, `update.html`, `pdf.html`

### 5.2 Estrutura mínima esperada por template

- `base.html` da área: layout da área, navegação, bloco de scripts e estilos específicos
- `index.html`: dashboard/resumo da área
- `list.html`: listagem com filtros, tabela/cards e integração com API/fetch
- `new.html`: criação
- `edit.html`: edição
- `view.html`: detalhe do registro com evidências e auditoria
- `export.html`: tela de exportação com seleção de formato e período

Mesmo que a funcionalidade ainda não esteja pronta, esses templates devem existir ao menos como stubs renderizáveis para manter a isonomia estrutural do projeto.

Listagens devem seguir padrão `API + fetch` já adotado no projeto.

## 6. JavaScript por área

Criar arquivos em `static/sigo/assets/js/<app>/`:

- `<area-kebab>-form.js`
- `<area-kebab>-view.js`
- `<area-kebab>-export.js`

Arquivos compartilhados do app podem coexistir, como no SIOP:

- `async-form.js`
- `async-list.js`

### 6.1 Regra de criação dos scripts

Mesmo que o módulo ainda esteja em implementação, os scripts principais da área já devem existir como stubs:

- `form.js` para submissão e validação via fetch
- `view.js` para ações do detalhe, evidências e refresh parcial
- `export.js` para exportação assíncrona

Se a área ainda não usar um dos scripts, ele deve existir com stub mínimo e comentário curto indicando uso futuro. Isso evita divergência estrutural entre áreas.

### 6.2 Convenções de integração

- usar sempre endpoints `api/...` como fonte de dados
- `list.html` deve consumir `api_<area>`
- `view.html` deve consumir `api_<area>_detail` quando houver carregamento assíncrono
- `export.html` deve consumir `api_<area>_export`
- preferir `fetch` com `FormData` ou JSON conforme o caso
- manter compatibilidade com scanners de segurança e parsers conservadores

Regras:

- evitar sintaxe não suportada pelos scanners de segurança, quando houver dúvida
- manter escapes e sanitização em renderização HTML dinâmica
- usar rotas da API para listagem e detalhe

### 6.3 Padrão Detalhado de Criação de JavaScript

Para diretrizes completas e detalhadas sobre criação de arquivos JavaScript, incluindo:
- Padrão IIFE e encapsulamento
- Organização de funções
- Segurança (XSS prevention)
- Padrões reutilizáveis (forms, exports, photo management)
- Checklist de criação
- Migração de código legado

**Consulte**: [padrao_create_javascript.md](padrao_create_javascript.md)

O documento define o padrão **oficial** para arquivos `.js` com base no SIOP como referência de excelência.

### 6.4 Padrão Detalhado de CSS

Para diretrizes completas de CSS, incluindo:
- convenções de nomenclatura e semântica de classes
- uso obrigatório de design tokens (spacing, radius, transitions, colors)
- padrão de breakpoints alinhado ao Bootstrap
- estratégia de dark mode por variáveis
- checklist de qualidade e compatibilidade com legado

**Consulte**: [padrao_css.md](padrao_css.md)

O documento define o padrão **oficial** para arquivos `.css` e evolução do estilo sem quebra visual.

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
- stubs de todas as views obrigatórias criados, mesmo sem lógica final
- templates principais criados
- scripts JS principais criados com nome oficial da área
- nomenclatura de templates, rotas e JS aderente ao padrão SIOP
- serializers de listagem e detalhe implementados
- serviços de criação/edição implementados
- filtros em `query.py` implementados
- documentação da área atualizada em `docs/`
- testes mínimos adicionados

## 12. Prompt recomendado para AI (copiar e usar)

"Crie uma nova área no projeto Django seguindo estritamente o padrão arquitetural de `docs/padrao_create_module_project.md`, usando o SIOP como régua de nomenclatura e estrutura. Gere estrutura completa com models (se necessário), services, query, serializers, support, views, urls, templates, scripts JS, exportações e testes mínimos. Crie também os stubs obrigatórios de views, templates e JS mesmo quando a lógica ainda não estiver implementada. Use pasta em snake_case, path em kebab-case, nomes de rota em snake_case e compatibilidade com o padrão API + fetch." 

## 13. Roadmap arquitetural (unificado)

Este roadmap consolida o antigo ToDo arquitetural no mesmo documento de padrão.

### 13.1 Objetivo

Consolidar a base atual de `SIGO`, `SIOP` e `SESMT` sem reescrever o projeto,
priorizando:

- arquitetura por domínio
- separação clara de responsabilidades
- previsibilidade para evolução
- maior cobertura contra regressão
- performance operacional e segurança

### 13.2 Diagnóstico resumido

Hoje o projeto já tem uma base forte em:

- validação de domínio com `clean()` e `full_clean()`
- constraints e índices relevantes
- bom reaproveitamento de anexos, fotos, assinatura e geolocalização
- padrão visual consistente entre módulos
- fluxos `API + fetch` nas áreas novas e maduras
- organização por área já bem resolvida no `SIOP`

Ponto de atenção:

- diferença de maturidade estrutural entre `SIOP` e `SESMT`, especialmente na
  concentração de lógica em `sesmt/views.py`

### 13.3 Prioridade alta

#### 1. Extrair regra de negócio das views

Objetivo:

- deixar a camada HTTP mais fina e mais segura para manutenção

Entregáveis:

- criar `services.py` por área para regras de criação, edição, finalização e notificações
- criar `query.py` por área para filtros, paginação, dashboards e agregações
- mover helpers específicos para `support.py` quando fizer sentido

Critério de conclusão:

- a view passa a orquestrar request/response
- regra operacional deixa de ficar espalhada em função HTTP

#### 2. Ampliar cobertura de testes por fluxo crítico

Objetivo:

- endurecer o projeto contra regressões

Entregáveis:

- testes de criação e edição nas áreas críticas
- testes de transição de status
- testes de notificações por módulo
- testes de exportação
- testes de persistência de fotos, geolocalização e assinatura
- testes de filtros reais das listagens

Critério de conclusão:

- fluxos operacionais principais ficam cobertos de forma previsível

#### 3. Consolidar padrões de resposta de API

Objetivo:

- tornar o contrato do front mais previsível

Entregáveis:

- revisar payloads de sucesso e erro
- padronizar mensagens de validação
- centralizar helpers de resposta JSON quando couber

Critério de conclusão:

- todas as áreas novas respondem de maneira consistente para `fetch`

### 13.4 Prioridade média

#### 4. Revisar consultas, índices e ordenações com base no uso real

Objetivo:

- manter performance sem inflar custo de escrita

Entregáveis:

- revisar consultas mais usadas em dashboards e listagens
- revisar índices compostos periodicamente
- medir ganhos antes de adicionar índices pouco seletivos

Critério de conclusão:

- índices passam a refletir padrão real de consulta, não só hipótese

#### 5. Refinar nomenclatura técnica e consistência do código

Objetivo:

- reduzir ruído e ambiguidade no código

Entregáveis:

- revisar nomes fora do padrão idiomático do Django
- padronizar nomes de classes, funções e arquivos novos
- reduzir legados de nomenclatura onde o risco de compatibilidade for baixo

### 13.5 Prioridade baixa

#### 6. Melhorar observabilidade e manutenção operacional

Objetivo:

- facilitar suporte e diagnóstico

Entregáveis:

- logging mais claro por módulo
- padronização de erros operacionais
- auditoria técnica mais consistente em áreas críticas

#### 7. Revisão contínua de segurança de upload e evidências

Objetivo:

- reforçar proteção sobre arquivos e conteúdo operacional

Entregáveis:

- revisar limites e validações de upload
- revisar fluxo de persistência de assinatura e foto
- revisar políticas de leitura e download dos arquivos

### 13.6 Ordem sugerida de execução

1. Extrair `services` e `query` das áreas do `SESMT`.
2. Ampliar cobertura de testes dos fluxos principais.
3. Padronizar contratos de API e respostas JSON.
4. Continuar o pente fino de performance, nomenclatura e observabilidade.

