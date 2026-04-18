# Line Scope

The `line` scope runs once per karaoke line. Both `template` and `code`
directives can target it.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template line,{\an5\pos($line_center,$line_middle)\fad(200,200)}
```

## Variables

The `line_*` variables and the generated-line variables (`layer`,
`actor`, `loop_i`, `loop_n`) are available. See [Scopes](./scopes.md).

## Behavior

- One generated line is produced per iteration (or per source line, when
  no `loop` is used).
- The source text is appended by default; use `no_text` to skip it.

## Examples

Fade the whole line in and out:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template line,{\fad(200,200)}
```

Assign a per-line value for later use:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code line,hue = line_i % 3
```

## See Also

- [Word Scope](./word-scope.md)
- [Syllable Scope](./syllable-scope.md)
- [Modifiers](./modifiers.md)
