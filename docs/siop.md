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

## 4.1 Controle de acesso por grupo

Para o controle de acesso por namespace funcionar corretamente, os grupos abaixo devem existir no Django com nomenclatura exata:

- `group_siop`
- `group_sesmt`
- `group_reportos`

Comportamento atual:

- usuários com `group_siop` acessam SIOP
- usuários com `group_sesmt` acessam SESMT
- superusuário acessa todos os módulos
- `group_reportos` é utilizado no roteamento pós-login e organização de acesso

## 5. Regras operacionais relevantes

### 5.0 Ocorrências (integração e listagem)

- listagem principal prioriza `data_ocorrencia` para exibição de data/hora
- ocorrências criadas por sincronização SESMT usam descrição em múltiplas linhas com marcador técnico na primeira linha
- notificações e textos de apoio foram padronizados para o termo "módulo" (substituindo "contexto")

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

- Ocorrências
- Acesso de Terceiros
- Acesso de Colaboradores
- Achados e Perdidos
- Controle de Ativos
- Controle de Chaves
- Crachás Provisórios
- Efetivo
- Liberação de Acesso

Filtros disponíveis na Exportação Geral por área:

- Ocorrências: período, natureza, área e status
- Acesso de Terceiros: período, status, P1, empresa, nome, documento e placa
- Acesso de Colaboradores: período, status, P1, nome, documento e placa
- Achados e Perdidos: período, tipo, situação, status e área
- Controle de Ativos: período, status, ativo, destino, responsável e documento
- Controle de Chaves: período, status, área, chave, responsável e documento
- Crachás Provisórios: período, status, crachá, nome e documento
- Efetivo: período, plantão, posto, responsável e observação
- Liberação de Acesso: período, empresa e solicitante

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
- ajuste visual da descrição de ocorrência para destacar a primeira linha quando houver marcador de sincronização

## 9. Próximos passos

- continuar limpeza conservadora de assets legados sem uso real
- ampliar testes de borda em APIs e listagens assíncronas
- manter padronização visual e textual entre áreas
