# Legado do Controle BC no projeto antigo

Referência levantada a partir de:

- `/home/administrador/sources_app/siop_src/siop`
- foco em `Atendimento`, `Flora` e `Fauna`

Objetivo deste documento:

- registrar como os campos e fluxos existiam no projeto antigo
- evitar redescoberta manual durante a evolução do `SESMT`
- servir de base para decisão do que reaproveitar, adaptar ou simplificar

## Visão geral do legado

No projeto antigo, `Controle BC` era a área-mãe de navegação:

- template: `/home/administrador/sources_app/siop_src/siop/templates/controle_bc/controle_bc.html`
- view: `/home/administrador/sources_app/siop_src/siop/view/vw_controle_bc/controle_bc.py`

Ele funcionava como central para:

- `Atendimento`
- `Manejo`
- `Flora`

Importante:

- `Fauna` não existia como módulo visual isolado
- o tema de fauna estava acoplado ao fluxo de `Manejo`

## Atendimento

### Fontes no legado

- template principal: `/home/administrador/sources_app/siop_src/siop/templates/atendimento/atendimento.html`
- consulta: `/home/administrador/sources_app/siop_src/siop/templates/atendimento/consulta.html`
- listagem: `/home/administrador/sources_app/siop_src/siop/templates/atendimento/list.html`
- detalhe: `/home/administrador/sources_app/siop_src/siop/templates/atendimento/view.html`
- view: `/home/administrador/sources_app/siop_src/siop/view/vw_atendimento/atendimento.py`
- service: `/home/administrador/sources_app/siop_src/siop/services/atendimento.py`
- JS do formulário: `/home/administrador/sources_app/siop_src/static/js/atendimento.js`
- JS da consulta/lista: `/home/administrador/sources_app/siop_src/static/js/atendimento-records.js`
- model: `/home/administrador/sources_app/siop_src/siop/models.py`

### Estrutura visual do formulário

O formulário antigo era dividido nestes blocos:

1. `Dados da Pessoa`
2. `Contato`
3. `Dados do Atendimento`
4. `Saúde`
5. `Remoção e Encaminhamento`
6. `Acompanhante`
7. `Testemunhas`
8. `Anexos e Evidências`

### Campos do formulário antigo

#### Dados da Pessoa

- `tipo_pessoa`
- `recusa_atendimento`
- `pessoa_nome`
- `pessoa_documento`
- `pessoa_orgao_emissor`
- `pessoa_sexo`
- `pessoa_data_nascimento`
- `pessoa_nacionalidade`

#### Contato

- `contato_endereco`
- `contato_bairro`
- `contato_cidade`
- `contato_estado`
- `contato_provincia`
- `contato_pais`
- `contato_telefone`
- `contato_email`

Observação:

- o formulário alternava `estado` e `provincia` conforme o país

#### Dados do Atendimento

- `data_atendimento`
- `area_atendimento`
- `local`
- `tipo_ocorrencia`
- `responsavel_atendimento`
- `atendimentos`
- `primeiros_socorros`
- `descricao`

#### Saúde

- `doenca_preexistente`
- `descricao_doenca`
- `alergia`
- `descricao_alergia`
- `plano_saude`
- `nome_plano_saude`
- `numero_carteirinha`

#### Remoção e Encaminhamento

- `seguiu_passeio`
- `houve_remocao`
- `transporte`
- `encaminhamento`
- `hospital`
- `medico_responsavel`
- `crm`

#### Acompanhante

- `possui_acompanhante`
- `acompanhante_nome`
- `acompanhante_documento`
- `acompanhante_orgao_emissor`
- `acompanhante_sexo`
- `acompanhante_data_nascimento`
- `grau_parentesco`

#### Testemunhas

Fluxo dinâmico com até 2 blocos:

- `testemunhas[i][nome]`
- `testemunhas[i][documento]`
- `testemunhas[i][telefone]`
- `testemunhas[i][data_nascimento]`

#### Anexos e Evidências

- `fotos` via câmera
- `fotos` via dispositivo
- `geo_latitude`
- `geo_longitude`
- `assinatura_atendido`

### Campos persistidos no model legado

Conforme `ControleAtendimento`:

- `tipo_pessoa`
- `pessoa`
- `contato`
- `area_atendimento`
- `local`
- `data_atendimento`
- `tipo_ocorrencia`
- `possui_acompanhante`
- `acompanhante_pessoa`
- `grau_parentesco`
- `doenca_preexistente`
- `descricao_doenca`
- `alergia`
- `descricao_alergia`
- `plano_saude`
- `nome_plano_saude`
- `numero_carteirinha`
- `primeiros_socorros`
- `atendimentos`
- `recusa_atendimento`
- `responsavel_atendimento`
- `seguiu_passeio`
- `houve_remocao`
- `transporte`
- `encaminhamento`
- `hospital`
- `medico_responsavel`
- `crm`
- `descricao`
- `testemunhas`
- `anexos`
- `fotos`
- `geolocalizacoes`
- `assinaturas`
- `hash_atendimento`

### Regras percebidas no legado

- `tipo_pessoa`, `pessoa`, `area_atendimento`, `local`, `data_atendimento`, `tipo_ocorrencia`, `descricao` e `responsavel_atendimento` eram obrigatórios
- `acompanhante_pessoa` e `grau_parentesco` eram exigidos quando `possui_acompanhante=True`
- `transporte`, `encaminhamento` e `hospital` eram exigidos quando `houve_remocao=True`
- `descricao_doenca` era exigida quando `doenca_preexistente=True`
- `descricao_alergia` era exigida quando `alergia=True`
- `nome_plano_saude` era exigido quando `plano_saude=True`

### Aspectos relevantes para o novo SESMT

O legado de `Atendimento` era bem rico e orientado a campo. Os pontos mais relevantes para reaproveitamento conceitual são:

- separação clara por blocos de formulário
- pessoa + contato + saúde + remoção no mesmo registro
- testemunhas como grupo dinâmico
- evidências com foto, geolocalização e assinatura

## Flora

### Fontes no legado

- template principal: `/home/administrador/sources_app/siop_src/siop/templates/flora/flora.html`
- consulta: `/home/administrador/sources_app/siop_src/siop/templates/flora/consulta.html`
- listagem: `/home/administrador/sources_app/siop_src/siop/templates/flora/list.html`
- detalhe: `/home/administrador/sources_app/siop_src/siop/templates/flora/view.html`
- view: `/home/administrador/sources_app/siop_src/siop/view/vw_flora/flora.py`
- service: `/home/administrador/sources_app/siop_src/siop/services/flora.py`
- model: `/home/administrador/sources_app/siop_src/siop/models.py`

### Estrutura visual do formulário

O formulário de `Flora` era mais enxuto e de campo:

- data e hora do registro
- responsável pelo registro
- área
- localização
- ação inicial
- medições básicas
- descrição
- foto antes
- foto depois
- geolocalização

### Campos do formulário antigo

- `data_hora_inicio`
- `responsavel_registro`
- `area`
- `local`
- `acao_inicial`
- `diametro_peito`
- `altura_total`
- `descricao`
- `foto_antes`
- `foto_depois`
- `latitude`
- `longitude`

### Campos persistidos no model legado

Conforme `Flora`:

- `responsavel_registro`
- `local`
- `area`
- `popular`
- `especie`
- `nativa`
- `estado_fitossanitario`
- `descricao`
- `justificativa`
- `acao_inicial`
- `acao_final`
- `fotos`
- `geolocalizacoes`
- `data_hora_inicio`
- `data_hora_fim`
- `diametro_peito`
- `altura_total`
- `zona`
- `responsavel`

### Campos exibidos na listagem e no detalhe

Na listagem antiga apareciam:

- `ID`
- `Data/Hora Início`
- `Data/Hora Fim`
- `Área`
- `Localização`
- `Responsável`
- `Ação Inicial`
- `Status`

No detalhe antigo apareciam, além dos básicos:

- `popular`
- `especie`
- `diametro_peito`
- `altura_total`
- `acao_final`
- `geolocalizacao`
- `justificativa`
- `foto_antes`
- `foto_depois`

### Regras percebidas no legado

- `responsavel_registro`, `data_hora_inicio`, `local`, `area`, `acao_inicial` e `descricao` eram obrigatórios
- `data_hora_fim` não podia ser anterior a `data_hora_inicio`
- `diametro_peito` e `altura_total`, quando informados, precisavam ser maiores que zero

### Aspectos relevantes para o novo SESMT

O legado de `Flora` sugere um fluxo prático de campo:

- início do registro
- área/local
- ação inicial
- medições
- descrição
- evidência fotográfica antes/depois
- geolocalização

## Fauna

### Situação no legado

No projeto antigo, `Fauna` não existia como módulo visual independente.

Ela aparecia dentro do fluxo de `Manejo`.

### Fontes no legado

- view: `/home/administrador/sources_app/siop_src/siop/view/vw_manejo/manejo.py`
- model: `/home/administrador/sources_app/siop_src/siop/models.py`
- catálogo: `/home/administrador/sources_app/siop_src/siop/catalago/catalogo_fauna.json`

### Catálogo de fauna no legado

Classes identificadas:

- `Anfíbio`
- `Ave`
- `Mamífero`
- `Réptil`

Exemplos do catálogo:

- `Ave`: `Beija-flor`, `Coruja`, `Curicaca`, `Gavião`, `Gralha-azul`, `Tucano`, `Urubu`
- `Mamífero`: `Bugio`, `Capivara`, `Gato-do-mato`, `Lobo-guará`, `Quati`, `Veado`
- `Réptil`: `Cobra`, `Lagarto`

### Campos persistidos no model de Manejo

Como a fauna antiga vivia em `Manejo`, os campos relevantes eram:

- `data_hora`
- `classe`
- `nome_cientifico`
- `nome_popular`
- `estagio_desenvolvimento`
- `area_captura`
- `local_captura`
- `descricao_local`
- `importancia_medica`
- `realizado_manejo`
- `responsavel_manejo`
- `area_soltura`
- `local_soltura`
- `descricao_local_soltura`
- `acionado_orgao_publico`
- `orgao_publico`
- `numero_boletim_ocorrencia`
- `motivo_acionamento`
- `observacoes`
- `geolocalizacoes`
- `fotos`
- `anexos`

### Leitura para o novo SESMT

Se o novo projeto quiser uma área de `Fauna`, há dois caminhos naturais:

1. manter o legado conceitual de `Fauna` dentro de `Manejo`
2. separar `Fauna` como módulo próprio, mas reaproveitando:
   - classe taxonômica
   - espécie/nome popular
   - captura/soltura
   - acionamento de órgão público
   - fotos, anexos e geolocalização

## Recomendação prática para evolução do SESMT

### Atendimento

Vale considerar do legado:

- blocos de formulário por contexto
- saúde/remoção/acompanhante/testemunhas
- assinatura
- evidências e geolocalização

### Flora

Vale considerar do legado:

- medições simples
- ação inicial/final
- foto antes/depois
- geolocalização
- trilha temporal de início/fim

### Fauna

Vale considerar do legado:

- catálogo taxonômico por classe
- fluxo de captura/soltura
- acionamento institucional
- observações operacionais

## Resumo executivo

- `Controle BC` antigo era uma central de navegação
- `Atendimento` era o formulário mais rico e estruturado
- `Flora` era um fluxo de campo enxuto, com fotos e geolocalização
- `Fauna` não era um módulo separado; estava embutida no `Manejo`

Este documento deve ser usado como referência funcional, não como obrigação de réplica literal. O ideal no novo `SESMT` é reaproveitar o que faz sentido operacionalmente e simplificar o que for excesso para a nova realidade do projeto.
