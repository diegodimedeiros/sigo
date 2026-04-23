# Relatório de padronização dos catálogos

## Padrão aplicado

- Estrutura uniforme com `catalogo`, `tipo` e `itens` ou `grupos`.

- Cada opção passou a usar `chave` e `valor`.

- Chaves técnicas em `snake_case`, sem acentos.

- Ajustes pontuais de grafia, acentuação e plural inconsistente (`Outro`/`Outros`).

- Remoção apenas do que era claramente redundante.


## Alterações por arquivo

### catalogo_achados_perdidos.json

- Padronizado em grupos com chave/valor.

- Mantidos todos os itens; não havia duplicação real.


### catalogo_area.json

- Padronizado para grupos com itens chave/valor.

- Remoção preventiva de duplicatas internas por grupo (nenhuma relevante encontrada).


### catalogo_bc.json

- Transformado em lista padronizada.

- Mantido nome completo como metadado, apelido em valor.


### catalogo_choices_resgate.json

- Padronizado.

- Removidos espaços excedentes.

- Nenhuma duplicata real encontrada.


### catalogo_colaborador.json

- Padronizados nomes para Title Case.

- Padronizados setores: 'Ciop'→'CIOP' e 'Exp. Visitante'→'Experiência do Visitante'.

- Removidas duplicatas por nome (nenhuma encontrada).


### catalogo_encaminhamento.json

- Padronizado.

- 'Outros' ajustado para 'Outro'.

- 'Pronto Socorro' ajustado para 'Pronto-socorro'.


### catalogo_fauna.json

- Padronizado.

- Mantidos todos os itens.


### catalogo_flora.json

- Padronizado com títulos consistentes.

- Responsáveis convertidos para lista padronizada com nome completo como metadado.


### catalogo_natureza.json

- Padronizado.

- Categoria 'Outros' normalizada para 'Outro'.

- Correção ortográfica: 'Ausencia de energia'→'Ausência de energia'.


### catalogo_p1.json

- Convertido para lista chave/valor.


### catalogo_primeiros_socorros.json

- Padronizado.

- 'Outros' ajustado para 'Outro'.


### catalogo_sexo.json

- Convertido para lista chave/valor.

- Mantidos os 3 valores.


### catalogo_tipo_ocorrencia.json

- Padronizado.

- 'Outros' ajustado para 'Outro'.


### catalogo_tipo_pessoa.json

- Padronizado.

- 'Outros' ajustado para 'Outro'.


### catalogo_transporte.json

- Padronizado.

- Removido item redundante 'UBER' por já existir 'Transporte por aplicativo'.

- Padronizado texto para 'Transporte por aplicativo'.


### catalogo_uf.json

- Padronizado em lista chave/valor.

- Mantidos todos os estados/UFs informados.


## Exemplo de montagem de catálogo

Exemplo de catálogo estruturado por grupos:

```json
{
	"catalogo": "nome_do_catalogo",
	"descricao": "Descrição opcional do catálogo",
	"tipo": "grupos",
	"grupos": [
		{
			"chave": "grupo_1",
			"valor": "Nome do Grupo 1",
			"descricao": "Descrição opcional do grupo",
			"itens": [
				{
					"chave": "item_1",
					"valor": "Item 1",
					"ativo": true,
					"ordem": 1
				},
				{
					"chave": "item_2",
					"valor": "Item 2",
					"ativo": true,
					"ordem": 2
				}
			]
		},
		{
			"chave": "grupo_2",
			"valor": "Nome do Grupo 2",
			"itens": [
				{
					"chave": "item_a",
					"valor": "Item A"
				},
				{
					"chave": "item_b",
					"valor": "Item B"
				}
			]
		}
	],
	"metadados": {
		"versao": 1,
		"data_criacao": "2026-04-08",
		"ativo": true
	}
}
```


## Observações importantes

- Nem toda repetição foi removida. Em `catalogo_area`, por exemplo, itens como `Banheiro Feminino` aparecem em áreas diferentes e fazem sentido por contexto.

- Alguns nomes comerciais ou operacionais, como lojas e locais, foram mantidos sem alteração quando não havia certeza de erro.

- `catalogo_bc` e `responsavel_registro` em `catalogo_flora` parecem representar a mesma base de pessoas em contextos diferentes. Eles foram padronizados, mas não fundidos automaticamente para evitar quebrar integrações existentes.


## Próximo passo recomendado

- Consolidar todos os catálogos em um único arquivo-mestre versionado.

- Definir quando o front/sistema deve usar `chave` e quando deve exibir `valor`.

- Centralizar catálogos compartilhados, como pessoas responsáveis, para evitar divergência futura.
