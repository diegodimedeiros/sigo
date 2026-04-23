# Catálogos e Convenções

Os catálogos do projeto ficam em:

- `sigo_core/catalogos`

Objetivo deste documento:

- padronizar estrutura e semântica dos catálogos
- reduzir risco de quebra entre backend, frontend e dados persistidos
- orientar evolução com compatibilidade retroativa controlada

## Estrutura base

Formato mais comum:

```json
{
  "catalogo": "nome_catalogo",
  "tipo": "lista",
  "itens": [
    {
      "chave": "valor_tecnico",
      "valor": "Texto exibido"
    }
  ]
}
```

## Identificação e versionamento

Todo catálogo novo ou alterado deve considerar versionamento lógico no próprio arquivo,
mesmo sem alterar nome físico do JSON.

Campos recomendados:

- `versao`: inteiro incremental (`1`, `2`, `3`)
- `atualizado_em`: data ISO (`YYYY-MM-DD`)
- `compat`: bloco opcional para chaves legadas aceitas temporariamente

Exemplo:

```json
{
  "catalogo": "catalogo_exemplo",
  "versao": 2,
  "atualizado_em": "2026-04-16",
  "tipo": "lista",
  "compat": {
    "chaves_legadas": ["valor_antigo"]
  },
  "itens": [
    {"chave": "valor_novo", "valor": "Valor novo"}
  ]
}
```

## Campos adicionais já usados

Dependendo do catálogo, podem existir campos extras como:

- `setor`
- `funcao`
- `area`
- `numero`
- `nome_completo`
- `grupos`

## Convenções atuais

- `chave` é o valor persistido no banco
- `valor` é o texto principal exibido
- quando houver agrupamento, o front pode usar `grupos` ou filtros auxiliares
- metadados extras devem existir para simplificar filtro, resumo ou auditoria

## Catálogos operacionais relevantes

- `catalogo_ativos.json`
  - organizado em grupos como `Rádio` e `Tablet`
- `catalogo_cracha_provisorio.json`
  - lista de crachás disponíveis
- `catalogo_chaves.json`
  - inclui área, número e nome da chave
- `catalogo_colaborador.json`
  - inclui nome completo, função, setor e área
- `catalogo_bc.json`
  - lista de bombeiros civis usada no `Efetivo`

## Recomendação de manutenção

- evitar duplicar no catálogo informações que já são salvas em campos independentes no banco, exceto quando o catálogo representa o item físico
- manter `chave` estável mesmo quando o texto exibido mudar
- documentar mudanças estruturais de catálogo nesta pasta `docs/`
- quando uma chave técnica precisar ser corrigida, preferir camada temporária de compatibilidade no loader antes de remover suporte ao valor antigo

## Checklist pré-deploy

Antes de publicar alteração em catálogo:

- validar JSON estruturalmente (sem vírgula extra, sem chave duplicada)
- confirmar que toda `chave` nova tem `valor` correspondente
- confirmar que nenhuma `chave` existente foi removida sem plano de migração
- revisar impacto em filtros, listagens e exportações que consumem o catálogo
- revisar impacto em dados já persistidos no banco
- incluir camada de compatibilidade para chaves legadas (quando aplicável)
- atualizar este documento quando houver mudança de estrutura semântica
- executar `manage.py check` e teste funcional mínimo da área impactada

## Migração de chaves legadas (exemplos)

### Exemplo 1: correção ortográfica de chave técnica

Cenário:

- legado: `facilites`
- alvo: `facilities`

Estratégia:

1. adicionar suporte duplo no loader (`facilites` e `facilities`)
2. manter persistência nova apenas com `facilities`
3. mapear leitura antiga para chave nova durante período de transição
4. migrar dados existentes por script/migration de dados
5. remover suporte da chave antiga após janela de estabilização

### Exemplo 2: renomear chave sem quebrar histórico

Cenário:

- legado: `cracha_provisorio`
- alvo: `cracha`

Estratégia:

1. manter `cracha_provisorio` em `compat.chaves_legadas`
2. introduzir item novo com `chave: cracha`
3. no serializer/query, normalizar ambos para `cracha`
4. atualizar UI para escrever apenas `cracha`
5. remover legado quando não houver mais registros antigos em uso

## Política de remoção de legado

Uma chave legada só pode ser removida quando:

- não existir mais dado ativo dependente dela
- os fluxos de leitura histórica estiverem cobertos por teste
- o time estiver alinhado com a remoção (registro em changelog interno)
- houver ao menos um ciclo de release com compatibilidade dupla

## Compatibilidade atual

- `catalogo_cracha_provisorio.json` usa `cracha_provisorio`
- `catalogo_funcoes_ativos.json` usa `facilities`
- o loader ainda aceita `facilites` como legado para leitura e migração gradual dos dados existentes
