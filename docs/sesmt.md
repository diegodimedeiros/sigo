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

Áreas atuais:

- sesmt/atendimento/
- sesmt/manejo/
- sesmt/flora/
- sesmt/himenopteros/

No nível do app:

- dashboard_views.py para home e notificações
- urls.py com import direto de cada área
- views.py mantido como fachada de compatibilidade

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

## 7. Próximos passos

- continuar extração de regra pesada de views para services/query
- ampliar cobertura de testes de cenários de borda
- manter isonomia estrutural com o padrão oficial em docs/padrao_create_module_project.md
