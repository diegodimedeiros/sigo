# SESMT

## 1. Visão geral

SESMT é um módulo operacional já em produção funcional, estruturado por domínios e alinhado ao padrão arquitetural do projeto.

## 2. Estado atual

Áreas em fluxo real:

- Atendimento
- Manejo
- Flora
- Monitor Himenóptero

Situação arquitetural atual:

- views separadas por área
- utilitários compartilhados extraídos para `view_shared.py`
- camadas de serviço e consulta criadas por domínio
- contrato API mais estável para integração com fetch
- fluxo web padronizado entre áreas

## 3. Estrutura arquitetural

O módulo segue estrutura por área com camadas:

- views.py para camada HTTP
- services.py para regra de negócio
- query.py para filtros e consultas
- serializers.py para payloads de API
- support.py e common.py para utilitários

No nível do app:

- `view_shared.py` com helpers e constantes de catálogo compartilhados entre todas as áreas
- dashboard_views.py para home e notificações
- urls.py com import direto de cada área
- views.py mantido como fachada de compatibilidade

Áreas atuais:

- sesmt/atendimento/
- sesmt/manejo/
- sesmt/flora/
- sesmt/himenopteros/

## 4. Fluxos padrão

Fluxo web por área:

- index
- list
- new
- edit
- view
- export

Fluxo API por área:

- api_<area>
- api_<area>_detail
- api_<area>_export

Integração principal:

- API + fetch

## 5. Resumo funcional por área

### 5.1 Atendimento

Cobertura atual:

- identificação e contato da pessoa
- dados de atendimento e saúde
- acompanhante e testemunhas
- fotos, geolocalização e assinatura
- exportação geral e PDF do registro

### 5.2 Manejo

Cobertura atual:

- abertura e finalização operacional
- captura e soltura com evidências
- geolocalização de captura e soltura
- exportação geral e PDF do registro

### 5.3 Flora

Cobertura atual:

- abertura e finalização
- avaliação de condição e ação realizada
- evidências fotográficas e geolocalização
- exportação geral e PDF do registro

### 5.4 Monitor Himenóptero

Cobertura atual:

- identificação de ocorrência
- avaliação de risco
- ação realizada e justificativa técnica
- isolamento de área
- fotos, geolocalização, exportação e PDF

Catálogo da área:

- sigo_core/catalogos/catalogos/catalogo_himenopteros.json

## 6. Referências de evolução

Base de evolução do módulo:

- sesmt/models.py
- fluxo novo do próprio projeto
- referência funcional histórica de Controle BC para Atendimento, Manejo e Flora

## 7. Atualizações visuais e textuais

Mudanças recentes aplicadas no módulo:

- padronização dos títulos e descrições de telas `new` para o formato "Novo Registro de ..."
- ajuste do hero de exportação de atendimento com remoção da ação de retorno no cabeçalho
- adoção do seletor de temas com opções `light`, `dark`, `forest` e `aqua` no topo do módulo
- adequação da paleta do tema claro para hero e botões principais em azul `#0e75eb`
- revisão de contraste e estados de botões no tema escuro com paleta ciano para ações primárias

## 8. Próximos passos

- continuar extração de regra pesada de views para services/query
- ampliar cobertura de testes de cenários de borda
- manter isonomia estrutural com o padrão oficial em docs/padrao_create_module_project.md

## 9. Integração SESMT -> SIOP (finalizada)

Implementação consolidada para replicação automática de registros SESMT em Ocorrências SIOP.

Arquivo central:

- sesmt/sesmt_to_siop_sync.py

Bootstrap dos signals:

- sesmt/apps.py (método ready)

Padrão técnico aplicado em todas as áreas:

- receiver post_save por modelo
- criação/uso de usuário técnico `sigo_sistema`
- idempotência por marcador em `descricao` com prefixo por área + ID SESMT
- create/update da mesma Ocorrência SIOP quando o mesmo registro SESMT é alterado
- campos fixos de integração: `bombeiro_civil=True` e `status=True`

Mapeamento por área:

1. Atendimento

- origem: ControleAtendimento
- tipo_pessoa: valor do próprio atendimento
- data_ocorrencia: data_atendimento
- natureza: assistencial
- tipo: atendimento_bombeiro_civil
- area/local: area_atendimento/local
- descricao: resumo do atendimento com ID e responsável pelo atendimento

2. Manejo

- origem: Manejo
- tipo_pessoa: bombeiro_civil
- data_ocorrencia: data_hora
- natureza: ambiental
- tipo: animal_manejo
- area/local: area_captura/local_captura
- descricao: resumo do manejo com ID e responsável pelo manejo

3. Flora

- origem: Flora
- tipo_pessoa: bombeiro_civil
- data_ocorrencia: data_hora_inicio
- natureza: ambiental
- tipo: condicao
- area/local: area/local
- descricao: resumo de flora com ID e responsável pelo registro

4. Himenóptero

- origem: Himenoptero
- tipo_pessoa: bombeiro_civil
- data_ocorrencia: data_hora_inicio
- natureza: ambiental
- tipo: evento_himenoptero
- area/local: area/local
- descricao: resumo de himenóptero com ID e responsável pelo registro

Catálogos alinhados para o fluxo:

- sigo_core/catalogos/catalogos/catalogo_natureza.json
- sigo_core/catalogos/catalogos/catalogo_tipo_pessoa.json
