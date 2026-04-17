# SIGO

Sistema Integrado de Gestão Operacional.

O projeto reúne módulos internos com interface administrativa em Django, layout compartilhado e organização por domínio operacional.

## Módulos

- `SIGO`: autenticação, perfil, notificações e modelos compartilhados
- `SIOP`: operação, portaria, controle e auditoria
- `SESMT`: saúde, segurança do trabalho e meio ambiente

## Áreas disponíveis

**SIOP**

- `Ocorrências`
- `Acesso de Terceiros`
- `Acesso de Colaboradores`
- `Achados e Perdidos`
- `Controle de Ativos`
- `Controle de Chaves`
- `Crachás Provisórios`
- `Efetivo`
- `Liberação de Acesso`

**SESMT**

- `Atendimento`
- `Manejo`
- `Flora`
- `Monitor Himenóptero`

## Stack

- Python
- Django
- SQLite para ambiente local
- Kaiadmin como base visual
- ReportLab para exportação PDF

## Estrutura

```text
sigo/
  autenticacao, perfil, notificacoes e modelos compartilhados

sigo_core/
  configuracao do projeto
  helpers compartilhados
  catalogos padronizados
  utilitarios de exportacao e anexos

siop/
  modulo operacional
  areas separadas entre pacotes e modulos por responsabilidade:
    dashboard_views.py
    download_views.py
    common.py
    notificacoes.py
    view_shared.py
    ocorrencias/
    acesso_terceiros/
    achados_perdidos/
    acesso_colaboradores/
    controle_ativos/
    controle_chaves/
    crachas_provisorios/
    efetivo/
    liberacao_acesso/
    views.py

sesmt/
  modulo de saude e seguranca
  views separadas por area:
    core_views.py
    atendimento/
    manejo/
    flora/
    himenopteros/
    views.py como fachada de compatibilidade
```

## Funcionalidades implementadas

- login e logout
- perfil do usuário com troca de foto e senha
- avatar de operador salvo no banco
- dark mode
- layout base compartilhado entre módulos
- paginação padrão nas listagens
- dashboard operacional do `SIOP` separado por área
- notificações por módulo
- rótulos de ação padronizados no front, como `Exportar`
- anexos em áreas que exigem evidência documental
- exportação PDF por registro nos resumos das áreas implementadas
- exportação geral em XLSX e CSV nas áreas administrativas e operacionais do `SIOP`, incluindo:
  - `Acesso de Colaboradores`
  - `Controle de Ativos`
  - `Controle de Chaves`
  - `Crachás Provisórios`
  - `Efetivo`
  - `Liberação de Acesso`
- formulários assíncronos com `fetch` no padrão do `SIOP` nas áreas implementadas do módulo
- APIs JSON padronizadas nas áreas implementadas do `SIOP`
- `SESMT > Atendimento`, `Manejo`, `Flora` e `Monitor Himenóptero` com fluxo real em `API + fetch` para `new`, `edit`, `list`, `view` e `export`
- persistência de fotos, geolocalização e assinatura nas áreas do `SESMT` que exigem evidência operacional
- exportação PDF por registro também nas áreas implementadas do `SESMT`
- normalização de campos string concentrada em `save()`/helpers nos models mais recentes, com `clean()` focado em validação
- helper compartilhado no `BaseModel` para preenchimento de `unidade_sigla`
- padronização transversal de UX textual nos módulos `SIOP` e `SESMT` com:
  - estado vazio de listagem unificado em `Nenhum registro encontrado.`
  - título de dashboard unificado em `Últimos registros`
  - cards de dashboard `Últimos registros` alinhados para 6 colunas visíveis (incluindo `Ação`)
  - card `Fila operacional` com estrutura isonômica de 4 passos por área

## Fluxos já consolidados no SIOP

- `Acesso de Terceiros`: entrada, saída, anexos e exportação PDF
- `Acesso de Colaboradores`: entrada, saída, anexos, API, exportação e criação múltipla com persistência de `1 colaborador = 1 registro`
- `Achados e Perdidos`: recebimento, devolução, fotos, anexos, API e PDF
- `Controle de Ativos`: retirada, devolução, bloqueio de item em aberto, submit assíncrono e PDF
- `Controle de Chaves`: retirada, devolução, bloqueio de chave em aberto, submit assíncrono e PDF
- `Crachás Provisórios`: entrega, devolução, indisponibilidade enquanto em uso, submit assíncrono e PDF
- `Efetivo`: um registro por dia, composição operacional, submit assíncrono e PDF
- `Liberação de Acesso`: múltiplas pessoas por autorização, registro de chegada, anexos, integração operacional com `Acesso de Terceiros`, submit assíncrono e PDF

## Catálogos

Os catálogos ficam em:

- `sigo_core/catalogos/catalogos`

O padrão principal é:

- `chave`: valor técnico persistido
- `valor`: texto exibido

Alguns catálogos também incluem metadados extras, como:

- `setor`
- `funcao`
- `area`
- `numero`
- `nome_completo`
- agrupamentos por tipo

Notas atuais de compatibilidade:

- `catalogo_cracha_provisorio.json` usa o identificador corrigido `cracha_provisorio`
- `catalogo_funcoes_ativos.json` usa a chave técnica `facilities`
- o loader mantém compatibilidade com o valor legado `facilites` para evitar quebra em registros antigos

## Como rodar localmente

Crie e ative o ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Instale as dependências:

```bash
./.venv/bin/pip install -r requirements.txt
```

Aplique as migrações:

```bash
./.venv/bin/python manage.py migrate
```

Crie um superusuário:

```bash
./.venv/bin/python manage.py createsuperuser
```

Rode o servidor:

```bash
./.venv/bin/python manage.py runserver
```

## Comandos úteis

Validar o projeto:

```bash
./.venv/bin/python manage.py check
```

Rodar todos os testes:

```bash
./.venv/bin/python manage.py test
```

Rodar apenas o `SIOP`:

```bash
./.venv/bin/python manage.py test siop -v 1
```

## Documentação adicional

- [Visão geral do SIOP](docs/siop.md)
- [Visão geral do SESMT](docs/sesmt.md)
- [Catálogos e convenções](docs/catalogos.md)

## Seed opcional de desenvolvimento

Existe uma ferramenta isolada em `dev_seed/` para gerar massa local de teste.

Características:

- não faz parte dos módulos de domínio
- só entra no `INSTALLED_APPS` se a pasta `dev_seed/` existir
- pode ser removida depois sem impactar o restante do projeto

Uso:

```bash
./.venv/bin/python manage.py seed_dev --clear
```

Dependência opcional para dados mais ricos:

```bash
./.venv/bin/pip install -r requirements-dev-seed.txt
```

## Licença

Uso interno.
