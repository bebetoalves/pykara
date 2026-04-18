# Modifiers

Modifiers refine how a `template` directive runs. They follow the scope
token in the `Effect` field.

```ass
template syl loop 3 no_blank
```

## Reference

| Modifier | Argument | Scopes | Purpose |
|------------|----------|-------------------------------|----------------------------------------------------|
| `loop` | yes | `line`, `word`, `syl`, `char` | Repeat the template N times. |
| `no_blank` | no | `word`, `syl`, `char` | Skip empty words, syllables, or characters. |
| `no_text` | no | `line`, `word`, `syl`, `char` | Do not append source text to the output. |
| `fx` | yes | `syl` | Match only syllables with the given inline-fx tag. |
| `when` | yes | `line`, `word`, `syl`, `char` | Run only if the expression is truthy. |
| `unless` | yes | `line`, `word`, `syl`, `char` | Run only if the expression is falsy. |

## `loop`

```ass
template syl loop 3
template syl loop glow 2
```

- `loop N` — exposes `loop_i` and `loop_n`.
- `loop NAME N` — exposes `loop_NAME_i` and `loop_NAME_n`.
- `loop (EXPR)` / `loop NAME (EXPR)` — evaluates `EXPR` at runtime and
  uses the resulting positive integer.
- Multiple named loops combine as a cartesian product.
- Unnamed and named loops cannot be mixed.

## `no_blank`

Skip words, syllables, or characters that have no visible text.

## `no_text`

Do not append the source text to the generated line. Useful when the
template provides its own text.

## `fx`

```ass
template syl fx glow
```

Match only syllables tagged with the given inline-fx name.

## `when` / `unless`

```ass
template syl when (syl.i == 0)
template syl unless (syl.i == syl.n - 1)
```

- `when EXPR` — run only if truthy.
- `unless EXPR` — run only if falsy.
- Expressions use the same names available inside `!expr!`, such as
  `line.i`, `word.i`, `syl.i`, `char.i`, `style`, and `metadata`.

Parentheses are required when the expression contains spaces.
