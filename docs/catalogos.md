# Catálogos e Convenções

Os catálogos do projeto ficam em:

- `sigo_core/catalogos/catalogos`

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

## Compatibilidade atual

- `catalogo_cracha_provisorio.json` usa `cracha_provisorio`
- `catalogo_funcoes_ativos.json` usa `facilities`
- o loader ainda aceita `facilites` como legado para leitura e migração gradual dos dados existentes
