# Pykara Directive System

Pykara's directive system controls karaoke execution through **comment**
events in your ASS file. The `Effect` field selects a directive and its
scope; the `Text` field carries the template body or Python code.

## Quick Reference

| Directive | Scopes | Description |
|-----------|--------|-------------|
| `template <scope>` | `line`, `word`, `syl`, `char` | Generate effect lines from a template. |
| `code <scope>` | `init`, `line`, `word`, `syl` | Run Python code in the current scope. |

## Documentation

### Core Concepts

- **[Directive Types](./directives/types.md)**
- **[Scopes](./directives/scopes.md)**
- **[Modifiers](./directives/modifiers.md)**
- **[Interpolation](./directives/interpolation.md)**

### Scopes

- **[Init Scope](./directives/init-scope.md)**
- **[Line Scope](./directives/line-scope.md)**
- **[Word Scope](./directives/word-scope.md)**
- **[Syllable Scope](./directives/syllable-scope.md)**
- **[Char Scope](./directives/char-scope.md)**

## ASS Line Format

Directives use the standard ASS comment format:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\pos($syl_center,$syl_middle)}
```

- `Default,,` — Style name and an empty `Name` field.
- `0,0,0,` — Margin values.
- `template syl` — Directive keyword and scope (plus optional modifiers).
- `{\pos($syl_center,$syl_middle)}` — Template body.

Only source lines with `Effect=karaoke` are processed. Directives
themselves live in `Comment:` lines.

By default, a directive only applies to karaoke lines with the same
`Style` as the directive line. Add `all` after the scope to make a
directive global:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code syl all,shared = 1
```

## See Also

- [Tools](./tools.md)
