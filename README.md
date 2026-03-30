# SIGO

Sistema Integrado de Gestão Operacional.

O projeto centraliza módulos internos com interface administrativa baseada em Django, usando um layout comum e áreas organizadas por domínio.

## Módulos

- `SIGO`: portal principal, autenticação e perfil do usuário
- `SIOP`: operações
- `SESMT`: saúde e segurança

## Áreas já estruturadas

No `SIOP`:

- `Ocorrências`
- `Acesso de Terceiros`
- `Achados e Perdidos`

No `SESMT`:

- `Atendimento`
- `Manejo`
- `Flora`

## Stack

- Python
- Django
- SQLite para ambiente local
- Kaiadmin como base visual

## Estrutura

```text
sigo/
  autenticacao, perfil e modelos compartilhados

sigo_core/
  configuracao do projeto
  helpers compartilhados
  catalogos padronizados

siop/
  modulo operacional
  areas separadas por pasta:
    ocorrencias/
    acesso_terceiros/
    achados_perdidos/

sesmt/
  modulo de saude e seguranca
```

## Catálogos

Os catálogos padronizados ficam em:

- `sigo_core/catalogos/catalogos`

O padrão usado é:

- `chave`: valor técnico persistido no banco
- `valor`: texto exibido no front

## Como rodar localmente

Crie e ative um ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Aplique as migrações:

```bash
python manage.py migrate
```

Crie um superusuário:

```bash
python manage.py createsuperuser
```

Rode o servidor:

```bash
python manage.py runserver
```

## Comandos úteis

Validar projeto:

```bash
python manage.py check
```

Rodar testes:

```bash
python manage.py test
```

Rodar apenas o módulo `siop`:

```bash
python manage.py test siop -v 1
```

## Funcionalidades já presentes

- login e logout
- perfil do usuário com troca de foto e senha
- avatar de operador salvo no banco
- dark mode
- layout base compartilhado entre módulos
- paginação padrão nas listagens
- ordenação por clique nas tabelas reais
- exportação PDF por registro em áreas já implementadas

## Observações

- o projeto está em construção ativa
- a arquitetura está sendo organizada por área para evitar regras espalhadas
- o projeto antigo em `siop_src` está sendo usado como referência funcional de migração

## Licença

Uso interno.
