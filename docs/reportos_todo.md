# TODO ReportOS

Backlog tecnico para reduzir acoplamento `reportos -> sesmt`, endurecer a camada offline/PWA e organizar a evolucao do modulo com menor risco operacional.

## Objetivos

- reduzir dependencia de internals do `sesmt`
- melhorar seguranca e previsibilidade do modo offline
- criar uma base mais estavel para evolucao do `reportos`
- transformar o estado atual em backlog executavel

## Prioridade P0

### 1. Limpar caches offline no logout

Impacto: alto
Esforco: baixo para medio
Risco mitigado: exposicao de paginas autenticadas e catalogos em navegador compartilhado

Tarefas:

- interceptar o fluxo de logout para disparar limpeza de `CacheStorage`
- limpar ao menos os caches `reportos-pages`, `reportos-catalogos` e `reportos-static`
- desregistrar ou atualizar o `service worker` do `reportos` quando fizer sentido
- avaliar limpeza da fila do `Background Sync` associada ao `reportos-sesmt-sync`
- garantir que a limpeza aconteca antes do redirect final para login quando possivel

Criterios de pronto:

- apos logout, navegacao offline nao deve exibir HTML autenticado previamente aquecido
- catalogos offline nao devem permanecer acessiveis para usuario seguinte no mesmo navegador
- comportamento deve ser coberto por teste manual documentado

### 2. Expor estado real da fila offline

Impacto: alto
Esforco: medio
Risco mitigado: falsa percepcao de que a sincronizacao concluiu

Tarefas:

- criar mecanismo para consultar tamanho da fila offline real
- diferenciar na interface os estados `sem conexao`, `fila vazia`, `fila pendente`, `erro de sincronizacao`
- substituir o texto atual de status baseado apenas em conectividade por estado operacional real
- registrar horario do ultimo replay bem-sucedido quando viavel

Criterios de pronto:

- a interface nao deve mostrar `Fila pronta` quando houver itens pendentes
- o operador deve conseguir distinguir entre falta de internet e falha no replay

### 3. Congelar contratos publicos entre `reportos` e `sesmt`

Impacto: alto
Esforco: medio
Risco mitigado: quebra do `reportos` por refactor interno no `sesmt`

Tarefas:

- mapear e substituir dependencias a helpers privados com prefixo `_`
- extrair uma camada publica por dominio:
  - `atendimento`
  - `manejo`
  - `flora`
  - `himenopteros`
- mover para essa camada as operacoes reutilizadas por ambos:
  - `build_queryset`
  - `apply_filters`
  - `save_from_payload`
  - `serialize_list_item`
  - `serialize_detail`
  - `build_form_context`
  - `build_dashboard`
- fazer o `sesmt` usar essa nova camada antes de migrar o `reportos`

Criterios de pronto:

- `reportos` nao importa mais helpers privados de `sesmt.*.views`
- mudancas internas de view no `sesmt` nao devem quebrar o `reportos`

## Prioridade P1

### 4. Padronizar contratos de exportacao do `reportos`

Impacto: medio
Esforco: baixo
Risco mitigado: comportamento inconsistente entre exportacao HTML, API e PDF

Tarefas:

- definir regra unica para exportacoes do `reportos`
- revisar os fluxos atuais:
  - exportacao de lista
  - exportacao via API
  - PDF por registro
- alinhar mensagens de indisponibilidade com a regra escolhida
- revisar se o modo offline deve permitir, bloquear ou enfileirar exportacoes

Criterios de pronto:

- todos os canais de exportacao seguem a mesma politica
- mensagens de erro e indisponibilidade sao coerentes

### 5. Cobrir o `reportos` com testes de fluxo reais

Impacto: medio
Esforco: medio
Risco mitigado: regressao silenciosa ao mexer no `sesmt` ou no PWA

Tarefas:

- adicionar testes para `create` e `update` via API do `reportos`
- validar rewrite de URLs de evidencias em serializers adaptados
- testar permissao por `group_reportos`
- testar retorno de `api_catalogos`
- criar roteiro de teste manual para modo offline:
  - pagina aquecida
  - formulario sem conexao
  - retomada de conexao
  - replay de fila

Criterios de pronto:

- `reportos/tests.py` cobre comportamento funcional, nao apenas renderizacao basica
- roteiro manual de PWA fica documentado

### 6. Criar diagnostico offline do `reportos`

Impacto: medio
Esforco: medio
Risco mitigado: baixa observabilidade do comportamento offline

Tarefas:

- criar tela ou painel tecnico para:
  - versao do `service worker`
  - caches ativos
  - total de itens pendentes na fila
  - ultimo sync bem-sucedido
  - ultimo erro de sincronizacao
- disponibilizar acesso apenas a perfis autorizados ou via modo tecnico

Criterios de pronto:

- suporte e equipe conseguem diagnosticar estado offline sem inspecionar manualmente o navegador

## Prioridade P2

### 7. Remover duplicacao de rotas no `reportos`

Impacto: medio
Esforco: baixo
Risco mitigado: ruido de manutencao e ambiguidade em `reverse()`

Tarefas:

- revisar rotas duplicadas com o mesmo path e nomes diferentes
- manter apenas o nome necessario para cada destino
- corrigir referencias em templates e testes

Criterios de pronto:

- `reportos/urls.py` nao possui aliases desnecessarios para o mesmo path

### 8. Isolar assets compartilhados com nomenclatura mais neutra

Impacto: medio
Esforco: medio
Risco mitigado: acoplamento transversal por naming e ownership confuso

Tarefas:

- revisar uso de `static/sigo/assets/js/siop/async-form.js` dentro de `sesmt` e `reportos`
- mover assets compartilhados para pasta mais neutra, por exemplo `core/` ou `shared/`
- ajustar imports nos templates

Criterios de pronto:

- assets usados por mais de um modulo nao carregam nome de um dominio especifico

### 9. Versionar e invalidar melhor caches HTML do `reportos`

Impacto: medio
Esforco: medio
Risco mitigado: servir conteudo antigo ou de sessao anterior por tempo excessivo

Tarefas:

- revisar estrategia de cache de navegacao `NetworkFirst`
- avaliar invalidacao por versao de deploy
- definir politica de expurgo para HTML autenticado

Criterios de pronto:

- pages cache deixa de depender apenas de aquecimento oportunista
- deploys e trocas de sessao ficam mais previsiveis

## Sequencia recomendada

1. limpar caches no logout
2. expor estado real da fila offline
3. congelar contratos publicos `reportos -> sesmt`
4. padronizar exportacoes
5. ampliar testes do `reportos`
6. criar diagnostico offline
7. limpar rotas duplicadas
8. neutralizar naming de assets compartilhados
9. revisar invalidacao de cache HTML

## Mapa exato de acoplamento atual

Hoje o `reportos` consome contratos do `sesmt` em quatro dominios:

- `atendimento`
  - queryset base
  - anotacao de dashboard e lista
  - filtros
  - persistencia por payload
  - serializacao de lista e detalhe
  - contexto de formulario
  - exportacao
  - evidencias de foto e assinatura
  - catalogo de locais por area
- `manejo`
  - queryset base
  - anotacao de dashboard e lista
  - filtros
  - persistencia por payload
  - serializacao de lista e detalhe
  - contexto de formulario
  - exportacao
  - evidencias de foto
  - catalogos de locais e especies
- `flora`
  - queryset base
  - anotacao de dashboard e lista
  - filtros
  - persistencia por payload
  - serializacao de lista e detalhe
  - contexto de formulario
  - exportacao
  - evidencias de foto
  - catalogo de locais por area
- `himenopteros`
  - queryset base
  - anotacao de dashboard e lista
  - filtros
  - persistencia por payload
  - serializacao de lista e detalhe
  - contexto de formulario
  - exportacao
  - evidencias de foto
  - catalogo de locais por area

Consequencia:

- refactor interno no `sesmt` pode quebrar o `reportos` mesmo sem alterar regra de negocio

Direcao recomendada:

- extrair camada publica compartilhada por dominio
- fazer `sesmt` e `reportos` consumirem essa camada
- manter `reportos/contracts.py` como adaptador temporario e nao como destino final

## Definicao de pronto do backlog

O backlog pode ser considerado resolvido quando:

- o `reportos` nao depender mais de helpers privados do `sesmt`
- o logout limpar de forma confiavel os artefatos offline sensiveis
- a fila offline tiver estado observavel na interface
- os fluxos principais estiverem cobertos por testes de aplicacao e roteiro manual de PWA

## Andamento executado

### 2026-04-22 - etapa aplicada em codigo

Itens concluidos:

- limpeza defensiva de artefatos offline do `ReportOS` no logout
- limpeza de fallback ao carregar a tela de login
- reativacao e padronizacao das rotas de exportacao do `ReportOS`
- remocao das aliases duplicadas `*_home` nas rotas do `ReportOS`
- exibicao de detalhe textual para a fila offline na home do `ReportOS`
- consolidacao do acoplamento em fachadas locais por dominio dentro de `reportos/contracts.py`
- extracao de uma camada publica inicial em `sesmt/contracts.py`
- ampliacao inicial de testes de `sigo` e `reportos`
- criacao de tela tecnica de diagnostico offline do `ReportOS`
- migracao do asset compartilhado `async-form` para caminho neutro em `static/sigo/assets/js/shared/`

Resultado tecnico:

- o logout agora tenta remover caches `reportos-pages`, `reportos-catalogos`, `reportos-static`, caches `workbox-precache*`, service workers do escopo `/reportos/` e o banco `workbox-background-sync`
- a tela de login tambem executa limpeza best-effort, reduzindo risco de sobrar conteudo autenticado entre usuarios no mesmo navegador
- a home do `ReportOS` agora reserva espaco para detalhe da fila offline, permitindo status mais informativo do que apenas `Fila pronta`
- o `pwa-register.js` passou a consultar o tamanho real da fila do Workbox via IndexedDB e atualizar a interface com:
  - quantidade pendente
  - fila vazia
  - ultima sincronizacao conhecida
  - indisponibilidade de leitura da fila
- os formulários assincronos disparam evento local quando um envio entra em modo offline, ajudando a atualizar o status da fila
- as exportacoes de `atendimento`, `manejo`, `flora` e `himenopteros` no `ReportOS` voltaram a seguir o comportamento do `SESMT` em:
  - pagina de exportacao
  - API de exportacao
  - PDF por registro
- `reportos/views.py` deixou de depender de imports diretos de `sesmt.*.views` e passou a consumir somente fachadas locais:
  - `atendimento_contract`
  - `manejo_contract`
  - `flora_contract`
  - `himenopteros_contract`
- `reportos/contracts.py` deixou de implementar a fachada sozinho e passou a delegar para a camada publica do proprio `SESMT`
- `sesmt/contracts.py` agora concentra a superficie compartilhada entre modulos para:
  - queryset
  - filtros
  - persistencia
  - serializacao
  - dashboard
  - formulario
  - exportacao
  - evidencias
  - endpoints auxiliares de catalogo
- a superficie minima do contrato local agora cobre:
  - queryset
  - filtros
  - persistencia
  - serializacao
  - dashboard
  - formulario
  - exportacao
  - evidencias
  - endpoints auxiliares de catalogo
- a ausencia das aliases antigas `atendimento_home`, `manejo_home` e `flora_home` agora ficou protegida por teste
- o `ReportOS` agora possui cobertura funcional inicial de API para `atendimento` em:
  - criacao
  - update
  - rewrite de `redirect_url`
  - rewrite de URLs de evidencias
- o `ReportOS` agora possui cobertura funcional equivalente para:
  - `manejo`
  - `flora`
  - `himenopteros`
- a cobertura funcional atual do `ReportOS` valida, por dominio:
  - criacao via API
  - update via API
  - `redirect_url` no namespace `reportos`
  - rewrite de URLs de evidencias para rotas `reportos`
- o `SESMT` ganhou smoke test para proteger a existencia da nova camada publica de contratos
- a home do `ReportOS` agora expõe acesso direto para uma tela de diagnostico offline
- a tela de diagnostico offline mostra, neste navegador:
  - conectividade atual
  - estado do service worker do escopo `/reportos/`
  - quantidade pendente na fila offline
  - ultimo enfileiramento conhecido
  - ultima sincronizacao conhecida
  - disponibilidade de `IndexedDB`
  - disponibilidade de `CacheStorage`
  - lista de caches ativos
- o antigo asset compartilhado `static/sigo/assets/js/siop/async-form.js` foi neutralizado para `static/sigo/assets/js/shared/async-form.js`
- `SESMT`, `SIOP` e `ReportOS` passaram a apontar para o caminho compartilhado novo
- o caminho antigo foi mantido apenas como shim de compatibilidade

Validacao executada:

- `python3 -m py_compile sigo/views.py sigo/urls.py sigo/tests.py`
- `python3 -m py_compile reportos/contracts.py reportos/views.py reportos/urls.py reportos/tests.py`
- `python3 -m py_compile sesmt/contracts.py sesmt/views.py sesmt/tests.py`
- tentativa de execucao da suite Django com:
  - `python3 -m django --version`
  - `python3 manage.py test reportos sesmt sigo`
- resultado da tentativa:
  - ambiente atual sem `django` instalado no interpretador ativo
  - validacao completa de aplicacao ficou bloqueada por dependencia ausente
- validacao estatica por diff e inspeção dos arquivos alterados

Roteiro manual recomendado para fechamento do tema offline:

1. abrir `ReportOS`, confirmar registro do service worker e aquecimento inicial
2. desligar rede, abrir novamente a home e uma tela ja aquecida
3. criar um registro offline e confirmar que a home mostra fila pendente
4. religar rede e confirmar transicao para fila vazia com horario de ultimo sync
5. executar logout e verificar que uma nova sessao nao reutiliza HTML autenticado anterior
6. abrir a tela `Diagnóstico Offline` e confirmar:
   - service worker ativo no escopo `/reportos/`
   - cache `reportos-pages`
   - cache `reportos-catalogos`
   - cache `reportos-static`
   - contagem da fila coerente com o que foi enfileirado
7. repetir o fluxo para pelo menos:
   - `atendimento`
   - `manejo`
   - `flora`
   - `himenopteros`

Limitacoes atuais:

- a limpeza offline ainda e `best-effort` do lado cliente; nao existe confirmacao do navegador para todos os cenarios
- o desacoplamento `reportos -> sesmt` ainda e parcial; os helpers internos do `sesmt` continuam sendo usados por tras das fachadas locais
- a camada publica compartilhada entre `sesmt` e `reportos` agora existe, mas ainda atua como facade sobre implementacoes internas das views
- ainda falta migrar progressivamente o proprio `sesmt` para consumir mais dessa camada em vez de manter a logica principal nas views
- o diagnostico offline melhora a observabilidade, mas nao substitui a validacao manual em navegador real para confirmar replay e limpeza completa entre sessoes
- a suite Django completa continua pendente ate existir ambiente com dependencias instaladas e ativas
