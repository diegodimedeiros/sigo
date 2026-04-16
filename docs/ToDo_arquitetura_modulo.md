# ToDo de Arquitetura 10/10

Plano de evolução para levar o projeto a um nível de robustez, previsibilidade e manutenção compatível com um sistema Django maduro.

## Objetivo

Consolidar a base atual do `SIGO`, `SIOP` e `SESMT` sem reescrever o projeto, priorizando:

- arquitetura por domínio
- separação clara de responsabilidades
- previsibilidade para evolução
- maior cobertura contra regressão
- performance operacional e segurança

## Diagnóstico resumido

Hoje o projeto já tem uma base forte em:

- validação de domínio com `clean()` e `full_clean()`
- constraints e índices relevantes
- bom reaproveitamento de anexos, fotos, assinatura e geolocalização
- padrão visual consistente entre módulos
- fluxos `API + fetch` nas áreas novas e maduras
- organização por área já bem resolvida no `SIOP`

O principal ponto de atenção atual é a diferença de maturidade estrutural entre `SIOP` e `SESMT`, especialmente na concentração de lógica em [sesmt/views.py](/home/administrador/sources_app/sigo_src/sesmt/views.py).

## Prioridade alta

### 1. Refatorar a estrutura do `SESMT` por área

Objetivo:

- aproximar o `SESMT` do padrão já consolidado no `SIOP`

Entregáveis:

- quebrar [sesmt/views.py](/home/administrador/sources_app/sigo_src/sesmt/views.py) por área
- criar pacotes próprios para:
  - `atendimento/`
  - `manejo/`
  - `flora/`
  - `himenopteros/`
- separar views compartilhadas de dashboard, exportação, downloads e notificações

Critério de conclusão:

- o `SESMT` deixa de depender de um arquivo único grande para operar as áreas principais

### 2. Extrair regra de negócio das views

Objetivo:

- deixar a camada HTTP mais fina e mais segura para manutenção

Entregáveis:

- criar `services.py` por área para regras de criação, edição, finalização e notificações
- criar `queries.py` ou `query.py` por área para filtros, paginação, dashboards e agregações
- mover helpers específicos para `support.py` quando fizer sentido

Critério de conclusão:

- a view passa a orquestrar request/response
- regra operacional deixa de ficar espalhada em função HTTP

### 3. Formalizar a convenção arquitetural do projeto

Objetivo:

- transformar o padrão atual em regra explícita

Entregáveis:

- documentar convenções de:
  - estrutura de app
  - nomes de arquivos
  - fluxo `index/list/new/edit/view/export`
  - padrão `API + fetch`
  - padrão de resumo, auditoria e evidências
  - notificações
  - exportações

Critério de conclusão:

- novo código deixa de depender de memória informal para seguir o padrão do projeto

## Prioridade média

### 4. Ampliar a cobertura de testes por fluxo crítico

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

### 5. Consolidar padrões de resposta de API

Objetivo:

- tornar o contrato do front mais previsível

Entregáveis:

- revisar payloads de sucesso e erro
- padronizar mensagens de validação
- centralizar helpers de resposta JSON quando couber

Critério de conclusão:

- todas as áreas novas respondem de maneira consistente para `fetch`

### 6. Revisar consultas, índices e ordenações com base no uso real

Objetivo:

- manter performance sem inflar custo de escrita

Entregáveis:

- revisar consultas mais usadas em dashboards e listagens
- revisar índices compostos periodicamente
- medir ganhos antes de adicionar índices pouco seletivos

Critério de conclusão:

- índices passam a refletir padrão real de consulta, não só hipótese

## Prioridade baixa

### 7. Refinar nomenclatura técnica e consistência do código

Objetivo:

- reduzir ruído e ambiguidade no código

Entregáveis:

- revisar nomes fora do padrão idiomático do Django
- padronizar nomes de classes, funções e arquivos novos
- reduzir legados de nomenclatura onde o risco de compatibilidade for baixo

### 8. Melhorar observabilidade e manutenção operacional

Objetivo:

- facilitar suporte e diagnóstico

Entregáveis:

- logging mais claro por módulo
- padronização de erros operacionais
- auditoria técnica mais consistente em áreas críticas

### 9. Revisão contínua de segurança de upload e evidências

Objetivo:

- reforçar proteção sobre arquivos e conteúdo operacional

Entregáveis:

- revisar limites e validações de upload
- revisar fluxo de persistência de assinatura e foto
- revisar políticas de leitura e download dos arquivos

## Ordem sugerida de execução

1. Refatorar a estrutura do `SESMT` por área.
2. Extrair `services` e `queries` das áreas do `SESMT`.
3. Documentar a convenção arquitetural oficial do projeto.
4. Ampliar a cobertura de testes dos fluxos principais.
5. Padronizar contratos de API e respostas JSON.
6. Continuar o pente fino de performance, nomes e observabilidade.

## Primeiro passo recomendado

Começar pela refatoração estrutural do `SESMT`.

Motivo:

- é hoje o maior desvio em relação ao padrão já comprovado do projeto
- reduz risco futuro de manutenção
- prepara o terreno para testes, serviços e queries mais limpos
- melhora robustez sem exigir reescrita funcional

## Status atual

- [x] Refatorar a estrutura do `SESMT` por área
- [ ] Extrair regra de negócio das views
- [ ] Formalizar a convenção arquitetural do projeto
- [ ] Ampliar a cobertura de testes por fluxo crítico
- [ ] Consolidar padrões de resposta de API
- [ ] Revisar consultas, índices e ordenações com base no uso real
- [ ] Refinar nomenclatura técnica e consistência do código
- [ ] Melhorar observabilidade e manutenção operacional
- [ ] Revisão contínua de segurança de upload e evidências
