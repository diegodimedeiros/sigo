# SIOP

Visão geral do módulo operacional.

## Áreas implementadas

- `Ocorrências`
- `Acesso de Terceiros`
- `Achados e Perdidos`
- `Controle de Ativos`
- `Controle de Chaves`
- `Crachás Provisórios`
- `Efetivo`
- `Liberação de Acesso`

## Padrões do módulo

- páginas de `index`, `list`, `new`, `view`, `edit` e `export`
- resumo com card de `Ações rápidas`
- exportação PDF por item no resumo
- filtros e paginação nas listagens
- dashboard principal separado por área
- notificações no topo e página dedicada de notificações
- ações de interface padronizadas, incluindo o uso do rótulo `Exportar`
- formulários assíncronos via `fetch` quando a área já está no padrão novo do módulo
- organização de views por responsabilidade:
  - `dashboard_views.py` para dashboard e notificações
  - `download_views.py` para downloads compartilhados
  - `ocorrencias/views.py` para o domínio de ocorrências
  - `operacoes_views.py` para as telas operacionais
  - `operacoes/` para helpers compartilhados por tema
  - `views.py` e `operacoes_support.py` mantidos como compatibilidade fina

## Integração front-back

Hoje o `SIOP` usa modelo misto, mas com direção clara para submit assíncrono:

- `Ocorrências`
- `Controle de Ativos`
- `Controle de Chaves`
- `Crachás Provisórios`
- `Efetivo`
- `Liberação de Acesso`

Essas áreas já seguem o padrão de formulário assíncrono com resposta JSON e redirecionamento para o resumo.

Áreas com API própria e contrato JSON explícito:

- `Ocorrências`
- `Acesso de Terceiros`
- `Achados e Perdidos`

## APIs disponíveis

### Ocorrências

- `GET /siop/api/ocorrencias/`
- `GET /siop/api/ocorrencias/<pk>/`

### Acesso de Terceiros

- `GET /siop/api/acesso-terceiros/`
- `GET /siop/api/acesso-terceiros/<pk>/`

### Achados e Perdidos

- `GET /siop/api/achados-perdidos/`
- `GET /siop/api/achados-perdidos/<pk>/`

## Catálogos auxiliares expostos por API

- `GET /siop/api/catalogos/naturezas/`
- `GET /siop/api/catalogos/naturezas/tipos/`
- `GET /siop/api/catalogos/areas/`
- `GET /siop/api/catalogos/areas/locais/`
- `GET /siop/api/catalogos/tipos-pessoa/`
- `GET /siop/api/catalogos/tipos-ocorrencia/`

## Regras operacionais relevantes

### Controle de Ativos

- um ativo não pode ser retirado novamente enquanto não houver devolução
- o formulário já responde em JSON quando submetido via `fetch`

### Controle de Chaves

- uma chave não pode ser retirada novamente enquanto não houver devolução
- o formulário já responde em JSON quando submetido via `fetch`

### Crachás Provisórios

- um crachá não pode ser entregue novamente enquanto não houver devolução
- o formulário já responde em JSON quando submetido via `fetch`

### Efetivo

- só pode existir um registro por dia
- `Bombeiro Civil 1` e `Bombeiro Civil 2` não podem repetir a mesma pessoa
- o atributo Python do campo de manutenção foi normalizado para `manutencao`
- o formulário já responde em JSON quando submetido via `fetch`

### Liberação de Acesso

- um registro pode conter uma ou mais pessoas
- a chegada pode ser registrada por pessoa ou para todos
- ao registrar a chegada, o backend cria um item individual em `Acesso de Terceiros`
- o acompanhamento de chegada fica salvo no próprio registro por `chegadas_registradas`
- o cadastro e a edição já respondem em JSON quando submetidos via `fetch`

## Exportação PDF por item

Áreas com PDF por registro:

- `Ocorrências`
- `Acesso de Terceiros`
- `Achados e Perdidos`
- `Controle de Ativos`
- `Controle de Chaves`
- `Crachás Provisórios`
- `Efetivo`
- `Liberação de Acesso`

## Exportação geral

As áreas abaixo já possuem exportação consolidada em `PDF`, `XLSX` e `CSV` a partir da tela `export`:

- `Controle de Ativos`
- `Controle de Chaves`
- `Crachás Provisórios`
- `Efetivo`
- `Liberação de Acesso`

## Anexos

Atualmente há uso de anexos em áreas com necessidade documental, como:

- `Ocorrências`
- `Acesso de Terceiros`
- `Achados e Perdidos`
- `Liberação de Acesso`

## Testes

O módulo possui cobertura automatizada para:

- contratos das APIs
- fluxos de criação e edição
- regras de indisponibilidade
- notificações principais
- fluxos de chegada em `Liberação de Acesso`
- formulários assíncronos sem regressão nos fluxos principais
- exportações gerais das áreas operacionais novas
- cenários adicionais de validação nas áreas novas, como destino inválido, chave incompatível com área e chegada sem `P1`
