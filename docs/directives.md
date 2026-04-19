# Pykara Directive System

Pykara's directive system controls karaoke execution through **comment**
events in your ASS file. The `Effect` field selects a directive type and
scope; the `Text` field carries the directive body.

## Quick Reference

| Directive | Scopes | Description |
|--------------------|-------------------------------|----------------------------------------|
| `template <scope>` | `line`, `word`, `syl`, `char` | Generate effect lines from a template. |
| `patch <scope>` | `line`, `word`, `syl`, `char` | Inject tags into matching template output. |
| `code <scope>` | `setup`, `line`, `word`, `syl` | Run Python code in the current scope. |

## Documentation

### Core Concepts

- **[Directive Types](./directives/types.md)** — `template`, `patch`, and `code`.
- **[Scopes](./directives/scopes.md)** — execution frequency and scope rules.
- **[Variables](./directives/variables.md)** — every `$variable` exposed to templates.
- **[Objects](./directives/objects.md)** — object-style access inside `!expr!`.
- **[Modifiers](./directives/modifiers.md)** — directive modifier keywords.

### Scopes

- **[Setup Scope](./directives/setup-scope.md)**
- **[Line Scope](./directives/line-scope.md)**
- **[Word Scope](./directives/word-scope.md)**
- **[Syllable Scope](./directives/syllable-scope.md)**
- **[Char Scope](./directives/char-scope.md)**

## ASS Line Format

Directives use the standard ASS comment format:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\pos($syl_center,$syl_middle)}
```

- `Default` — Style name.
- `template syl` — Directive type and scope (plus optional modifiers).
- `{\pos($syl_center,$syl_middle)}` — Template body.

Only source lines with `Effect=karaoke` are processed. This applies
regardless of whether the lines are commented out or active. In the
output, karaoke source lines are always written back as comments.

By default, a directive only applies to karaoke lines with the same
`Style` as the directive line. Add `all` after the scope to make a
directive global:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code syl all,shared = 1
```
