# Directive Types

Two directive types are available. The first token of the `Effect` field
chooses the type.

## `template <scope>`

Declares a template body. For every execution in the target scope, one
generated line is appended to the output.

- **Scopes:** `line`, `word`, `syl`, `char`.
- **Modifiers:** `loop`, `no_blank`, `no_text`, `fx`, `when`, `unless`.
- **Body:** ASS override tags, plain text, `$variables`, and `!expressions!`.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\pos($syl_center,$syl_middle)}
```

The source syllable text is appended to the rendered body unless
`no_text` is used.

## `code <scope>`

Runs Python code. Values assigned here become available to later
directives as `$name` or `!name!`.

- **Scopes:** `init`, `line`, `word`, `syl`.
- **Modifiers:** none.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code init,main = color.ass(255, 128, 0)
```

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\1c!main!}
```

## Execution Order

1. All `code init` directives run once.
1. For each karaoke line: `line` directives run, then every word runs
   its `word` directives, every syllable runs its `syl` directives, and
   every character runs its `char` directives.

## See Also

- [Scopes](./scopes.md)
- [Modifiers](./modifiers.md)
- [Interpolation](./interpolation.md)
