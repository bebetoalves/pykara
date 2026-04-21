# Modifiers

Modifiers refine how a `template` or `mixin` directive runs. They follow
the scope token in the `Effect` field.

```ass
template syl loop 3 no_blank
```

## Reference

| Modifier | Directives | Argument | Scopes | Purpose |
|----------|------------|----------|-------------------------------|----------------------------------------------------|
| `loop` | `template` | yes | `line`, `word`, `syl`, `char` | Repeat the template N times. |
| `no_blank` | `template` | no | `line`, `word`, `syl`, `char` | Skip empty lines, words, syllables, or characters. |
| `no_text` | `template` | no | `line`, `word`, `syl`, `char` | Do not append source text to the output. |
| `prepend` | `mixin` | no | `line`, `word`, `syl`, `char` | Insert before the template body. |
| `layer` | `mixin` | integer | `line`, `word`, `syl`, `char` | Match templates that set this output layer. |
| `for` | `mixin` | actor name | `line`, `word`, `syl`, `char` | Match templates with this actor. |
| `fx` | `template`, `mixin` | yes | `syl` | Match only syllables with the given inline-fx tag. |
| `styles` | `template`, `code` | tuple variable | `setup`, `line`, `word`, `syl`, `char` | Apply only to karaoke events using one of the listed styles. |
| `when` | `template`, `mixin` | yes | `line`, `word`, `syl`, `char` | Run only if the expression is truthy. |
| `unless` | `template`, `mixin` | yes | `line`, `word`, `syl`, `char` | Run only if the expression is falsy. |

## `loop`

```ass
template syl loop 3
template syl loop glow 2
```

- `loop N` — repeats the template and exposes `loop_i` plus `loop_n`.
- `loop NAME N` — repeats the template and exposes `loop_NAME_i` plus `loop_NAME_n`.
- `loop (EXPR)` / `loop NAME (EXPR)` — evaluates `EXPR` at runtime and
  uses the resulting positive integer.
- Multiple named loops combine as a cartesian product.
- Unnamed and named loops cannot be mixed.

## `no_blank`

Skip lines, words, syllables, or characters that have no visible text.

## `no_text`

Do not append the source text to the generated line. Useful when the
template provides its own text.

## `fx`

```ass
template syl fx glow
```

Match only syllables tagged with the given inline-fx name.

## `styles`

```ass
template syl styles my_styles
```

```python
my_styles = ("Romaji", "Kanji", "Translation")
```

Apply a `template` or `code` declaration only to karaoke events whose
style is listed in the tuple. Pykara uses the matched karaoke style as
the reference style for measurements, exposes it through `style`, and
uses it as the output event style.

The argument must be a variable that resolves to a tuple of style names.
Every listed style must exist. A single literal style name is not
accepted.

## `prepend`

```ass
mixin syl prepend
```

Insert the mixin body before the template body instead of before the
source object text.

## `layer`

```ass
mixin syl layer 2
```

Apply the mixin only when the generated line has the given layer. This is
checked after the template body has run, so `!layer.set(2)!` inside the
template can select the mixin.

## `for`

```ass
mixin syl for lead
```

Apply the mixin only to templates whose `Name`/actor field is `lead`.

## `when` / `unless`

```ass
template syl when glow
template syl unless muted
template syl when (syl.i == 0)
template syl unless (syl.i == syl.n - 1)
```

- `when FLAG` / `unless FLAG` — read one variable or expression name.
- `when (EXPR)` / `unless (EXPR)` — use a longer Python expression.
- Expressions use the same names available inside `!expr!`, such as
  `line.i`, `word.i`, `syl.i`, `char.i`, `style`, and `metadata`.

Parentheses are required when the expression contains spaces.
