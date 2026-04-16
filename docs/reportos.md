# ReportOS

## 1. Visão geral

ReportOS é o módulo planejado para operação de campo, com evolução progressiva para uso em PWA.

Objetivo principal:

- abrir base funcional do módulo sem acoplamento prematuro
- preparar estrutura para crescimento por domínio
- reaproveitar padrões operacionais já consolidados no sistema

## 2. Estado atual

No momento, o módulo já existe na aplicação com base mínima:

- rota própria em /reportos/
- template dedicado
- card no menu lateral do SIGO

Situação funcional:

- módulo em fase inicial de estrutura
- sem acoplamento forte de regra de negócio
- pronto para evolução incremental por área

## 3. Base funcional de referência

O escopo inicial foi consolidado a partir da análise do legado de Controle BC,
Atendimento, Flora e Manejo/Fauna, já internalizado no repositório atual.

## 4. Frentes funcionais iniciais

### 4.1 Atendimento

Escopo inicial previsto:

- dados da pessoa
- contato
- dados do atendimento
- saúde
- remoção e encaminhamento
- acompanhante
- testemunhas
- evidências, geolocalização e assinatura

### 4.2 Flora

Escopo inicial previsto:

- data e hora do registro
- área e local
- ação inicial
- medição básica
- descrição
- foto antes e depois
- geolocalização

### 4.3 Fauna

Escopo inicial previsto:

- classe taxonômica
- espécie e nome popular
- área e local de captura
- soltura
- acionamento institucional
- evidências e geolocalização

## 5. Padrão arquitetural alvo

A evolução do módulo deve seguir o padrão oficial em docs/padrao_create_module_project.md:

- estrutura por área
- fluxo web index/list/new/edit/view/export
- APIs com contrato estável para fetch
- separação em views, services, query, serializers e support

## 6. Próximos passos

- iniciar primeira área operacional com o padrão oficial completo
- validar contrato API e fluxo de listagem assíncrona
- ampliar cobertura de testes a cada área incorporada
