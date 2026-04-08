# SIOP

Visão geral do módulo operacional.

## Áreas implementadas

- `Ocorrências`
- `Acesso de Terceiros`
- `Acesso de Colaboradores`
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
  - `common.py`, `notificacoes.py` e `view_shared.py` para infraestrutura compartilhada do módulo
  - `ocorrencias/views.py` para o domínio de ocorrências
  - pacotes próprios para `acesso_colaboradores`, `controle_ativos`, `controle_chaves`, `crachas_provisorios`, `efetivo` e `liberacao_acesso`
  - `views.py` mantido como compatibilidade fina
- models mais recentes alinhados ao padrão:
  - `clean()` para validação
  - normalização de strings em `save()`/helpers
  - preenchimento de `unidade_sigla` via helper comum do `BaseModel`

## Integração front-back

Hoje o `SIOP` já opera com `API + fetch` nas áreas implementadas do módulo.

As áreas com API própria e contrato JSON explícito incluem:

- `Ocorrências`
- `Acesso de Terceiros`
- `Acesso de Colaboradores`
- `Achados e Perdidos`
- `Controle de Ativos`
- `Controle de Chaves`
- `Crachás Provisórios`
- `Efetivo`
- `Liberação de Acesso`

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

### Acesso de Colaboradores

- `GET /siop/api/acesso-colaboradores/`
- `POST /siop/api/acesso-colaboradores/`
- `GET /siop/api/acesso-colaboradores/<pk>/`
- `POST /siop/api/acesso-colaboradores/<pk>/`

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

### Acesso de Colaboradores

- o formulário pode receber um ou mais colaboradores no cadastro
- ao salvar, o backend cria `1 registro por colaborador`
- a edição opera sempre sobre um único colaborador por item
- a criação aceita seleção por catálogo e digitação manual no cadastro
- a exibição de `P1` usa o rótulo do catálogo no front, exportação e PDF

## Exportação PDF por item

Áreas com PDF por registro:

- `Ocorrências`
- `Acesso de Terceiros`
- `Achados e Perdidos`
- `Acesso de Colaboradores`
- `Controle de Ativos`
- `Controle de Chaves`
- `Crachás Provisórios`
- `Efetivo`
- `Liberação de Acesso`

## Exportação geral

As áreas abaixo já possuem exportação consolidada em `XLSX` e `CSV` a partir da tela `export`:

- `Acesso de Colaboradores`
- `Controle de Ativos`
- `Controle de Chaves`
- `Crachás Provisórios`
- `Efetivo`
- `Liberação de Acesso`

## Anexos

Atualmente há uso de anexos em áreas com necessidade documental, como:

- `Ocorrências`
- `Acesso de Terceiros`
- `Acesso de Colaboradores`
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
- filtros reais de API em áreas novas, incluindo status, área, empresa, solicitante e paginação com `limit/offset`

## ToDo atual

- continuar a limpeza conservadora de assets legados do tema que não participam do projeto
- ampliar a profundidade dos testes em APIs, listagens assíncronas e cenários de borda
- manter o pente fino de padronização visual e textual entre as áreas do `SIOP`
