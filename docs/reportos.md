# ReportOS

## 1. Visão geral

ReportOS é o módulo de operação de campo do SIGO, construído como espelho operacional do SESMT com foco em uso mobile e funcionamento offline-first.

Objetivos atuais do módulo:

- registrar ocorrências em campo com interface simplificada
- permitir uso com conectividade intermitente
- reaproveitar regras de negócio já consolidadas no SESMT
- sincronizar submissões quando a conexão retornar

## 2. Estado atual

O módulo já está funcional e exposto em produção de código com:

- rota própria em /reportos/
- home com cards para as áreas operacionais
- namespace próprio no menu lateral do SIGO
- controle de acesso por grupo group_reportos
- Service Worker dedicado em /reportos/sw.js


Áreas atualmente disponíveis:

- Atendimento (formulário padronizado: required HTML + validação JS)
- Manejo (formulário padronizado: required HTML + validação JS)
- Flora (formulário padronizado: required HTML + validação JS)
- Himenópteros (formulário padronizado: required HTML + validação JS)

Cada área já possui fluxo web com:

- index
- listagem
- novo registro (com required HTML e validação JS nos campos obrigatórios)
- edição
- visualização
- API JSON correspondente


## 3. Comportamento operacional

O ReportOS reutiliza a lógica de negócio do SESMT, adaptando URLs, templates e comportamento de interface para contexto de campo.
Todos os formulários bloqueiam o envio caso campos obrigatórios estejam vazios, tanto online quanto offline, via required HTML e validação JS, garantindo isonomia e robustez.

Situação das exportações no ReportOS:

- exportações foram desativadas por decisão funcional
- botões de exportar foram substituídos por voltar nas telas do módulo
- endpoints de export API retornam indisponível
- exportação PDF por registro redireciona para a visualização com aviso

## 4. Recursos offline/PWA

Recursos já implementados:

- manifest próprio do ReportOS
- registro de Service Worker com escopo /reportos/
- cache de assets estáticos
- NetworkFirst para navegação nas rotas do módulo
- fallback offline para páginas não disponíveis em cache
- warm-up das rotas principais após sessão autenticada
- background sync para POSTs em /reportos/api/ e /sesmt/api/
- cache offline dos catálogos consumidos pelos formulários
- pré-carregamento do endpoint /reportos/api/catalogos/

Catálogos offline atualmente cobertos:

- locais por área
- espécies por classe para manejo

Os formulários de Atendimento, Flora, Manejo e Himenópteros consultam o cache de catálogos do ReportOS antes de depender de requisições parametrizadas.

## 5. Evidências, mídia e geolocalização

O módulo já carrega os scripts compartilhados necessários para operação em campo:

- gerenciamento de fotos
- captura de geolocalização
- envio assíncrono de formulários

Cobertura funcional atual:

- upload de fotos em formulários do ReportOS
- geolocalização em formulários compatíveis
- tratamento resiliente no formulário de Himenópteros para não abortar inicialização quando catálogo falhar

## 6. Arquitetura adotada

O ReportOS segue o padrão de espelhamento do SESMT:

- views do ReportOS orquestram renderização, rotas e adaptação de URLs
- regras de domínio continuam concentradas no SESMT
- serialização de detalhes/listagens é reaproveitada e ajustada para URLs do namespace reportos
- templates e JavaScript são especializados para uso em campo

## 7. Validação atual

Cobertura mínima automatizada já existente:

- renderização da home do módulo
- renderização das quatro subáreas
- renderização dos formulários novos
- resposta da API agregada de catálogos offline

Observação:

- ainda é recomendável validação manual em navegador para cenários offline reais, especialmente após atualização de Service Worker

## 8. Pendências

Pendências restantes conhecidas:

- versionar melhor os caches do Service Worker para evitar conteúdo obsoleto em rollout futuro
- ampliar cobertura de testes para cenários offline e fluxo de catálogos em navegador
- executar validação operacional completa online/offline nas rotas críticas em dispositivo móvel
