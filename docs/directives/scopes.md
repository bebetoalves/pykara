# Scopes

A **scope** controls how often a directive runs and which variables are
available when it runs. The scope keyword follows the directive type in
the `Effect` field.

## Available Scopes

| Scope | Directives | Runs |
|--------|--------------------|------------------------|
| `setup` | `code` | Once per document. |
| `line` | `code`, `template` | Once per karaoke line. |
| `word` | `code`, `template` | Once per word. |
| `syl` | `code`, `template` | Once per syllable. |
| `char` | `template` | Once per character. |

Each nested scope sees its own variables plus those of outer scopes.

## Scope Access

| Scope | Data Available |
|-------|----------------|
| `setup` | No per-line runtime data. |
| `line` | Generated-line variables plus `line_*`. |
| `word` | Everything from `line`, plus `word_*`. |
| `syl` | Everything from `word`, plus `syl_*`. |
| `char` | Everything from `syl`, plus `char_*`. |

For the complete variable list, see [Variables](./variables.md). For
object properties available inside `!expr!`, see
[Objects](./objects.md).
