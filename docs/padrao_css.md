# Padrão Oficial de CSS (SIGO)

Este documento define o padrão oficial para criação e evolução de CSS no projeto.

Objetivos:
- manter consistência visual entre módulos
- reduzir duplicação e dívida técnica
- facilitar manutenção e revisão
- preservar compatibilidade com Bootstrap

## 1. Princípios

- usar classes semânticas e legíveis (`.card-title`, `.notification-item`)
- evitar seletores excessivamente específicos (`#id .class div`)
- preferir classes em vez de IDs para estilo
- centralizar design tokens em variáveis CSS
- reduzir regras duplicadas (especialmente em dark mode)
- aplicar alterações incrementais e reversíveis

## 2. Convenções de nomenclatura

- classes: `kebab-case`
- componentes: prefixo por domínio quando fizer sentido (`notification-*`, `login-*`, `listing-*`)
- estados: `.is-*` (ex.: `.is-active`, `.is-unread`)
- evitar abreviações opacas (`.t1`, `.x2`)

## 3. Tokens obrigatórios

Definir e reutilizar tokens em `:root`:

- espaçamento: `--space-*`
- raios: `--radius-*`
- transições: `--transition-*`
- cores e superfícies: `--color-*`
- sombras: `--shadow-*`

Exemplo:

```css
:root {
  --space-2: 0.5rem;
  --space-4: 1rem;
  --space-6: 1.5rem;
  --radius-md: 0.75rem;
  --radius-lg: 1rem;
  --radius-pill: 999px;
  --transition-fast: 0.18s ease;
  --transition-base: 0.2s ease;
}
```

## 4. Breakpoints e responsividade

Padrão alinhado ao Bootstrap 5:

- `575.98px`
- `767.98px`
- `991.98px`
- `1199.98px`

Regras:
- não misturar `991px` com `991.98px`
- manter consistência por arquivo
- preferir ajustes por componente, evitando sobrescritas globais desnecessárias

## 5. Dark mode

Tema escuro deve priorizar troca por variáveis e não duplicação de blocos inteiros.

Recomendado:

```css
:root {
  --color-bg: #eef3f8;
  --color-text: #314257;
}

html[data-sigo-theme="dark"] {
  --color-bg: #0b1220;
  --color-text: #e2e8f0;
}

body {
  background: var(--color-bg);
  color: var(--color-text);
}
```

## 5.1 Temas suportados no projeto

O projeto passa a suportar quatro temas visuais via `html[data-sigo-theme]`:

- `light`
- `dark`
- `forest`
- `aqua`

Regras:

- `data-bs-theme` deve continuar restrito a `light` ou `dark` para compatibilidade com Bootstrap
- temas adicionais como `forest` e `aqua` devem sobrescrever tokens próprios em `data-sigo-theme`
- o seletor de temas deve refletir o estado atual por ícone, `aria-current` e classe `active`
- botões primários, labels, hero e sidebar devem receber overrides por tema somente quando houver necessidade visual real

## 6. Estrutura recomendada (evolutiva)

Enquanto o projeto usa arquivo central, a evolução deve seguir separação por responsabilidade:

- base (tipografia, reset, elementos globais)
- componentes (botões, cards, tabelas, notificações)
- features (dashboard, login, perfil)
- utilities (spacing helpers, display helpers)
- temas (light/dark por variável)

## 7. Checklist para novos estilos

- [ ] nome semântico e claro
- [ ] uso de tokens existentes (sem hardcode desnecessário)
- [ ] sem aumento desnecessário de especificidade
- [ ] breakpoint no padrão definido
- [ ] compatível com dark mode
- [ ] sem duplicação óbvia de regra

## 8. Compatibilidade com legado

Para trechos antigos com `var(--primary)`, `var(--text-muted)`, `var(--border)`:

- manter aliases de compatibilidade em `:root`
- em código novo, preferir `--color-primary`, `--color-text-muted`, `--color-border`

## 9. Referências de prática

Este padrão é compatível com práticas consolidadas de:
- MDN Web Docs
- W3C
- CSS Guidelines

Não copiar regras literalmente de fontes externas; adaptar ao contexto do projeto.

## 10. Convenção visual recente

Para o tema `light`, a paleta operacional adotada recentemente usa azul `#0e75eb` como cor principal de CTAs e heros contextuais.

Para o tema `dark`, as ações primárias recentes usam ciano `#7dd3fc` com contraste escuro no texto.

Temas `forest` e `aqua` mantêm identidade própria com overrides explícitos de botões, sidebar e hero.
