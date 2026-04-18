# Char Scope

The `char` scope runs once per character inside every syllable. Only
`template` directives may target it.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template char,{\pos($char_center,$char_middle)}
```

## Variables

The `line_*`, `word_*`, `syl_*`, and `char_*` variables are available.
Characters inherit the parent syllable's timing. See
[Variables](./variables.md) and [Objects](./objects.md).

## Behavior

- Accurate widths depend on the package's built-in font measurement
  dependencies.
- The source character text is appended by default; use `no_text` to
  skip it.
- `no_blank` skips whitespace characters.

## Example

Rotate each character slightly based on its index:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template char,{\pos($char_center,$char_middle)\frz!$char_i * 10!}
```
