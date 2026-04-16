# SESMT

Visão atual do módulo `SESMT`.

## Estado do módulo

Hoje o `SESMT` já tem quatro áreas em fluxo real:

- `Atendimento`
- `Manejo`
- `Flora`
- `Monitor Himenóptero`

Também já passou pela primeira etapa de refatoração estrutural:

- `sesmt/views.py` deixou de concentrar a implementação inteira do módulo
- as views foram separadas por área em:
  - `sesmt/atendimento/views.py`
  - `sesmt/manejo/views.py`
  - `sesmt/flora/views.py`
  - `sesmt/himenopteros/views.py`
- `sesmt/core_views.py` concentra a base compartilhada de navegação do módulo
- `sesmt/views.py` foi mantido como fachada de compatibilidade para não quebrar rotas e imports existentes

Essas áreas seguem o padrão do projeto para o fluxo web principal:

- `index`
- `list`
- `new`
- `edit`
- `view`
- `export`
- APIs de coleção e detalhe
- envio e leitura principal em `API + fetch`

Observação:

- o `PDF` individual por registro continua sendo entregue por rota direta de arquivo, no mesmo padrão usado nas outras áreas maduras do sistema

## Atendimento

A área de `Atendimento` já está em fluxo operacional real.

Hoje ela cobre:

- identificação da pessoa atendida
- contato e endereço
- dados do atendimento
- saúde
- destino
- acompanhante
- testemunhas
- fotos
- geolocalização
- assinatura
- exportação geral
- PDF do registro

Também segue regras herdadas do legado, como:

- recusa de atendimento com regra mínima
- comportamento específico para estrangeiro com `província`
- persistência de evidências e hashes

## Manejo

A área de `Manejo` foi separada em dois momentos operacionais:

- `abertura`
- `finalização`

Na prática:

- a abertura cobre captura
- a edição/finalização cobre soltura e fechamento operacional

Hoje ela já entrega:

- fotos de captura
- fotos de soltura
- geolocalização de captura
- geolocalização de soltura
- resumo separado por `Captura` e `Soltura`
- exportação geral
- PDF do registro

## Flora

A área de `Flora` também foi organizada em dois momentos:

- `abertura`
- `finalização`

Na abertura, o fluxo prioriza o registro inicial da ocorrência e das evidências do local.

Hoje a área já cobre:

- dados de registro
- avaliação das condições gerais
- ação realizada
- informações complementares
- foto antes
- foto depois
- geolocalização
- exportação geral
- PDF do registro

Também já existem travas de edição para preservar os dados de abertura que não devem ser alterados depois.

## Monitor Himenóptero

A área de `Monitor Himenóptero` foi criada para ocorrências com:

- abelhas
- vespas
- marimbondos

Hoje ela já cobre:

- dados de registro
- identificação do himenóptero
- avaliação de risco
- ação realizada
- observações
- justificativa técnica
- isolamento de área
- fotos
- geolocalização
- exportação geral
- PDF do registro

O catálogo próprio da área fica em:

- `sigo_core/catalogos/catalogos/catalogo_himenopteros.json`

E segue o padrão do projeto:

- `chave` persistida no banco
- `valor` exibido na interface

## Base funcional usada

O módulo foi evoluído a partir de:

- `sesmt/models.py`
- fluxos novos do próprio projeto
- referências documentadas em [legacy_siop_bc.md](/home/administrador/sources_app/sigo_src/docs/legacy_siop_bc.md)
- legado antigo de `Controle BC`, especialmente para `Atendimento`, `Manejo` e `Flora`

## Observações atuais

- o `SESMT` já deixou de ser frente futura e passou a ter áreas operacionais reais
- o padrão visual e estrutural do módulo foi alinhado ao restante do sistema
- as áreas novas seguem a mesma direção de `API + fetch` consolidada no `SIOP`
