# SIOP

## 1. Visão geral

SIOP é o módulo operacional mais maduro da base, servindo como referência de nomenclatura e estrutura para os demais módulos.

## 2. Áreas implementadas

- Ocorrências
- Acesso de Terceiros
- Acesso de Colaboradores
- Achados e Perdidos
- Controle de Ativos
- Controle de Chaves
- Crachás Provisórios
- Efetivo
- Liberação de Acesso

## 3. Estrutura arquitetural

Organização no nível do app:

- dashboard_views.py para dashboard e notificações
- download_views.py para downloads compartilhados
- common.py, notificacoes.py e view_shared.py para infraestrutura compartilhada
- pacote por domínio para as áreas operacionais
- views.py mantido como camada de compatibilidade

Padrão funcional dominante:

- fluxo web index/list/new/edit/view/export
- integração API + fetch
- respostas JSON padronizadas nas áreas novas
- validação de domínio via clean() e normalização de dados em save/helpers

## 4. APIs e integrações

O módulo opera com APIs por domínio e contrato explícito para consumo assíncrono.

Catálogos auxiliares expostos por API:

- /siop/api/catalogos/naturezas/
- /siop/api/catalogos/naturezas/tipos/
- /siop/api/catalogos/areas/
- /siop/api/catalogos/areas/locais/
- /siop/api/catalogos/tipos-pessoa/
- /siop/api/catalogos/tipos-ocorrencia/

## 5. Regras operacionais relevantes

### 5.1 Controle de Ativos

- ativo não pode ser retirado novamente sem devolução

### 5.2 Controle de Chaves

- chave não pode ser retirada novamente sem devolução

### 5.3 Crachás Provisórios

- crachá não pode ser entregue novamente sem devolução

### 5.4 Efetivo

- máximo de um registro por dia
- bombeiro civil 1 e 2 não podem repetir a mesma pessoa

### 5.5 Liberação de Acesso

- registro pode conter múltiplas pessoas
- chegada pode ser individual ou em lote
- chegada confirmada gera item individual em Acesso de Terceiros

### 5.6 Acesso de Colaboradores

- criação pode receber múltiplos colaboradores
- persistência cria um registro por colaborador
- edição opera em item individual

## 6. Exportações e evidências

Exportação por registro (PDF) disponível nas áreas operacionais principais.

Exportação geral (XLSX e CSV) consolidada nas áreas:

- Acesso de Colaboradores
- Controle de Ativos
- Controle de Chaves
- Crachás Provisórios
- Efetivo
- Liberação de Acesso

Uso de anexos documentais nas áreas com necessidade operacional relevante, incluindo ocorrências e fluxos de acesso.

## 7. Cobertura de testes

Cobertura automatizada atual inclui:

- contratos de API
- fluxos de criação e edição
- regras de indisponibilidade
- notificações principais
- cenários de chegada em Liberação de Acesso
- formulários assíncronos sem regressão
- exportações gerais
- filtros reais de listagem e paginação

## 8. Atualizações visuais e textuais

Mudanças recentes aplicadas no módulo:

- padronização dos títulos e descrições das telas `new` para o formato "Novo Registro de ..."
- revisão de textos de apoio nas áreas operacionais para reforçar cadastro operacional, evidências e rastreabilidade
- adoção do seletor de temas com opções `light`, `dark`, `forest` e `aqua` no topo do módulo
- adequação da paleta do tema claro para CTAs principais e variações label em azul `#0e75eb`
- manutenção de variações próprias para `forest` e `aqua`, com sidebar, hero e botões coerentes por tema

## 9. Próximos passos

- continuar limpeza conservadora de assets legados sem uso real
- ampliar testes de borda em APIs e listagens assíncronas
- manter padronização visual e textual entre áreas
