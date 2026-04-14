# Referência do Projeto Antigo: Controle BC, Atendimento, Flora e Fauna

Este documento consolida como as áreas do projeto legado em `/home/administrador/sources_app/siop_src/siop` estavam estruturadas, com foco em:

- `Controle BC`
- `Atendimento`
- `Flora`
- `Fauna` (aplicada dentro de `Manejo`)

O objetivo é servir como base de comparação e migração para o projeto atual.

## Estrutura Geral no Projeto Antigo

### Controle BC

Arquivos principais:

- `/home/administrador/sources_app/siop_src/siop/view/vw_controle_bc/controle_bc.py`
- `/home/administrador/sources_app/siop_src/siop/templates/controle_bc/controle_bc.html`

Leitura:

- `Controle BC` não era um CRUD próprio.
- Funcionava como uma central de navegação.
- A tela reunia 3 blocos:
  - `Atendimento`
  - `Manejo`
  - `Flora`

Na prática:

- `Controle BC` era um hub operacional.
- A lógica real vivia nas áreas filhas.

### Flora

Arquivos principais:

- `/home/administrador/sources_app/siop_src/siop/view/vw_flora/flora.py`
- `/home/administrador/sources_app/siop_src/siop/templates/flora/flora.html`
- `/home/administrador/sources_app/siop_src/siop/templates/flora/consulta.html`
- `/home/administrador/sources_app/siop_src/siop/templates/flora/list.html`
- `/home/administrador/sources_app/siop_src/siop/templates/flora/view.html`

Leitura:

- `Flora` já era uma área funcional de verdade.
- Tinha:
  - cadastro
  - listagem
  - visualização
  - busca
  - paginação
  - resposta parcial/AJAX
  - upload de fotos
  - geolocalização

### Fauna

Arquivos principais:

- `/home/administrador/sources_app/siop_src/siop/view/vw_manejo/manejo.py`
- `/home/administrador/sources_app/siop_src/siop/models.py`
- `/home/administrador/sources_app/siop_src/siop/catalago/catalogo_fauna.json`

Leitura:

- `Fauna` não existia como módulo/template isolado.
- O conceito de fauna entrava dentro de `Manejo`.
- O usuário escolhia:
  - `classe`
  - `espécie`
- Essas opções vinham do catálogo `catalogo_fauna.json`.

Então, no legado:

- `Fauna` era um domínio de catálogo e formulário dentro de `Manejo`
- não uma área visual independente como `Flora`

## Atendimento Antigo

Arquivos principais:

- `/home/administrador/sources_app/siop_src/siop/view/vw_atendimento/atendimento.py`
- `/home/administrador/sources_app/siop_src/siop/services/atendimento.py`
- `/home/administrador/sources_app/siop_src/siop/templates/atendimento/atendimento.html`
- `/home/administrador/sources_app/siop_src/siop/templates/atendimento/consulta.html`
- `/home/administrador/sources_app/siop_src/siop/templates/atendimento/list.html`
- `/home/administrador/sources_app/siop_src/siop/templates/atendimento/view.html`
- `/home/administrador/sources_app/siop_src/static/js/atendimento.js`
- `/home/administrador/sources_app/siop_src/static/js/atendimento-records.js`

### Como a área era organizada

No legado, `Atendimento` tinha:

- formulário rico de cadastro
- listagem em abas
- visualização em aba lateral/detalhe
- comportamento dinâmico em JS
- uso de catálogos
- anexos/fotos
- geolocalização
- assinatura do atendido
- testemunhas

### Campos do model `ControleAtendimento`

Base do registro:

- `tipo_pessoa`
- `pessoa`
- `contato`
- `area_atendimento`
- `local`
- `data_atendimento`
- `tipo_ocorrencia`

Acompanhante:

- `possui_acompanhante`
- `acompanhante_pessoa`
- `grau_parentesco`

Saúde:

- `doenca_preexistente`
- `descricao_doenca`
- `alergia`
- `descricao_alergia`
- `plano_saude`
- `nome_plano_saude`
- `numero_carteirinha`

Atendimento:

- `primeiros_socorros`
- `atendimentos`
- `recusa_atendimento`
- `responsavel_atendimento`
- `seguiu_passeio`

Remoção e encaminhamento:

- `houve_remocao`
- `transporte`
- `encaminhamento`
- `hospital`
- `medico_responsavel`
- `crm`

Descrição:

- `descricao`

Complementos:

- `testemunhas`
- `anexos`
- `fotos`
- `geolocalizacoes`
- `assinaturas`
- `hash_atendimento`

### Seções visuais do formulário antigo

O template `atendimento.html` organizava o cadastro em blocos:

1. `Dados da Pessoa`
2. `Contato`
3. `Dados do Atendimento`
4. `Saúde`
5. `Remoção e Encaminhamento`
6. `Acompanhante`
7. `Testemunhas`
8. `Anexos e Evidências`
9. `Geolocalização do Atendimento`
10. `Assinatura do Atendido`

### Campos visuais relevantes do formulário antigo

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

Até 2 blocos de testemunha, com:

- `nome`
- `documento`
- `telefone`
- `data_nascimento`

#### Anexos e evidências

- múltiplas fotos do atendimento
- upload por câmera
- upload por dispositivo
- lista visual das imagens adicionadas

#### Geolocalização

- `geo_latitude`
- `geo_longitude`

#### Assinatura

- `assinatura_atendido`

### Comportamento JS do Atendimento Antigo

O JS antigo fazia:

- atualização de `local` a partir de `área`
- alternância de `estado/província` conforme tipo de pessoa estrangeira
- abertura e fechamento de grupos condicionais
- doença/alergia/plano de saúde
- acompanhante
- remoção/transporte
- testemunhas
- geolocalização
- captura de assinatura em modal
- upload/listagem de fotos

Arquivos:

- `/home/administrador/sources_app/siop_src/static/js/atendimento.js`
- `/home/administrador/sources_app/siop_src/static/js/atendimento-records.js`

## Flora Antiga

Arquivos principais:

- `/home/administrador/sources_app/siop_src/siop/view/vw_flora/flora.py`
- `/home/administrador/sources_app/siop_src/siop/templates/flora/flora.html`
- `/home/administrador/sources_app/siop_src/siop/templates/flora/consulta.html`
- `/home/administrador/sources_app/siop_src/siop/templates/flora/list.html`
- `/home/administrador/sources_app/siop_src/siop/templates/flora/view.html`

### Campos do model `Flora`

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

### Campos visuais do formulário antigo de Flora

O template `flora.html` mostrava:

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
- lista da foto antes
- lista da foto depois
- `latitude`
- `longitude`

### Estrutura visual do legado em Flora

`Flora` no legado tinha:

- cadastro
- consulta em abas
- listagem
- detalhe
- status derivado de `data_hora_fim`
- preview de fotos
- preview de geolocalização

## Fauna Antiga

### Onde ela aparecia

Não existia template `fauna.html` próprio.

A fauna era descrita dentro de `Manejo`, via:

- `classe`
- `nome_cientifico`
- `nome_popular`
- `estagio_desenvolvimento`

e catálogo:

- `/home/administrador/sources_app/siop_src/siop/catalago/catalogo_fauna.json`

### Estrutura do catálogo `catalogo_fauna.json`

Grupos de classe:

- `Anfíbio`
- `Ave`
- `Mamífero`
- `Réptil`

Exemplos de espécies:

- `Perereca`
- `Coruja`
- `Quati`
- `Gambá`
- `Cobra`
- `Lagarto`
- `Outro`

### Campos do model `Manejo` ligados à fauna

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

## Leitura Resumida Para Migração

### O que o legado fazia bem

- formulário de `Atendimento` muito completo
- divisão do formulário em seções claras
- forte uso de lógica condicional no front
- `Flora` com fluxo de campo bem prático
- `Controle BC` como central de entrada das áreas
- `Fauna` bem encaixada dentro de `Manejo`

### O que isso sugere para o projeto atual

Se a ideia for usar o legado como referência:

- `Atendimento` do `SESMT` atual deve mirar o desenho do formulário antigo
- `Flora` futura do `SESMT` pode aproveitar quase toda a estrutura conceitual do legado
- `Fauna` não precisa nascer como módulo isolado se a intenção funcional continuar sendo `Manejo`
- `Controle BC` pode ser reinterpretado como uma central interna do `SESMT`, não necessariamente como entidade própria

## Arquivos de Referência

### Projeto antigo

- `/home/administrador/sources_app/siop_src/siop/models.py`
- `/home/administrador/sources_app/siop_src/siop/view/vw_controle_bc/controle_bc.py`
- `/home/administrador/sources_app/siop_src/siop/view/vw_atendimento/atendimento.py`
- `/home/administrador/sources_app/siop_src/siop/view/vw_flora/flora.py`
- `/home/administrador/sources_app/siop_src/siop/view/vw_manejo/manejo.py`
- `/home/administrador/sources_app/siop_src/siop/templates/controle_bc/controle_bc.html`
- `/home/administrador/sources_app/siop_src/siop/templates/atendimento/atendimento.html`
- `/home/administrador/sources_app/siop_src/siop/templates/atendimento/consulta.html`
- `/home/administrador/sources_app/siop_src/siop/templates/atendimento/list.html`
- `/home/administrador/sources_app/siop_src/siop/templates/atendimento/view.html`
- `/home/administrador/sources_app/siop_src/siop/templates/flora/flora.html`
- `/home/administrador/sources_app/siop_src/siop/templates/flora/consulta.html`
- `/home/administrador/sources_app/siop_src/siop/templates/flora/list.html`
- `/home/administrador/sources_app/siop_src/siop/templates/flora/view.html`
- `/home/administrador/sources_app/siop_src/siop/catalago/catalogo_fauna.json`
- `/home/administrador/sources_app/siop_src/static/js/atendimento.js`
- `/home/administrador/sources_app/siop_src/static/js/atendimento-records.js`
