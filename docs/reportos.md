# ReportOS

`ReportOS` e o modulo planejado para operacao de campo com foco em uso progressivo como `PWA`.

## Base funcional usada para iniciar o modulo

O escopo inicial foi consolidado a partir destes documentos:

- [legacy_siop_bc.md](/home/administrador/sources_app/sigo_src/docs/legacy_siop_bc.md)
- [referencia_siop_src_bc.md](/home/administrador/sources_app/sigo_src/docs/referencia_siop_src_bc.md)

## Frentes iniciais

### Atendimento

Baseado no legado de `ControleAtendimento`, com interesse principal em:

- dados da pessoa
- contato
- dados do atendimento
- saude
- remocao e encaminhamento
- acompanhante
- testemunhas
- evidencias, geolocalizacao e assinatura

### Flora

Baseado no legado de `Flora`, com interesse principal em:

- data e hora do registro
- area e local
- acao inicial
- medicao basica
- descricao
- foto antes e depois
- geolocalizacao

### Fauna

Baseada no legado de `Manejo`, onde fauna aparecia como dominio catalogado, com interesse principal em:

- classe taxonomica
- especie/nome popular
- area e local de captura
- soltura
- acionamento institucional
- evidencias e geolocalizacao

## Estado atual

Neste momento, `ReportOS` foi aberto como modulo proprio do sistema:

- rota: `/reportos/`
- template proprio
- card no menu lateral do `SIGO`

O objetivo desta primeira entrega e abrir a base do modulo sem acoplar regra de negocio prematura, usando a documentacao do legado como referencia oficial.
