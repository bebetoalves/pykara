# Scopes

A **scope** controls how often a directive runs and which variables are
available when it runs. The scope keyword follows the directive name in
the `Effect` field.

## Available Scopes

| Scope | Directives | Runs |
|-------|------------|------|
| `init` | `code` | Once per document. |
| `line` | `code`, `template` | Once per karaoke line. |
| `word` | `code`, `template` | Once per word. |
| `syl` | `code`, `template` | Once per syllable. |
| `char` | `template` | Once per character. |

Each nested scope sees its own variables plus those of outer scopes.

## Variable Groups

### Line (`line` scope and deeper)

| Variable | Description |
|----------|-------------|
| `line_start`, `line_end`, `line_dur`, `line_mid` | Timing in ms (and midpoint). |
| `line_i` | Line index. |
| `line_left`, `line_center`, `line_right`, `line_width` | Horizontal geometry. |
| `line_top`, `line_middle`, `line_bottom`, `line_height` | Vertical geometry. |
| `line_x`, `line_y` | Anchor position. |

### Word (`word` scope and deeper)

Words are separated by spaces in the karaoke text.

| Variable | Description |
|----------|-------------|
| `word_start`, `word_end`, `word_dur`, `word_kdur`, `word_mid` | Timing (`kdur` in centiseconds). |
| `word_i`, `word_n` | Word index and total count. |
| `word_left`, `word_center`, `word_right`, `word_width` | Horizontal geometry. |
| `word_top`, `word_middle`, `word_bottom`, `word_height` | Vertical geometry. |
| `word_x`, `word_y` | Anchor position. |

### Syllable (`syl` scope and deeper)

| Variable | Description |
|----------|-------------|
| `syl_start`, `syl_end`, `syl_dur`, `syl_kdur`, `syl_mid` | Timing (`kdur` in centiseconds). |
| `syl_i`, `syl_n` | Syllable index and total count. |
| `syl_left`, `syl_center`, `syl_right`, `syl_width` | Horizontal geometry. |
| `syl_top`, `syl_middle`, `syl_bottom`, `syl_height` | Vertical geometry. |
| `syl_x`, `syl_y` | Anchor position. |

### Character (`char` scope only)

| Variable | Description |
|----------|-------------|
| `char_i`, `char_n` | Character index and count within the syllable. |
| `char_left`, `char_center`, `char_right`, `char_width` | Horizontal geometry. |
| `char_top`, `char_middle`, `char_bottom`, `char_height` | Vertical geometry. |
| `char_x`, `char_y` | Anchor position. |

### Generated Line

| Variable | Description |
|----------|-------------|
| `layer` | Output layer. |
| `actor` | Actor name. |
| `loop_i`, `loop_n` | Current iteration and total (when a single loop is active). |

## Object-Style Access

Inside `!expressions!`, the same data is reachable through objects:

```
!syl.center!
!word.i!
!line.dur!
!style.primary_color!
!metadata.res_x!
```

Available objects: `line`, `word`, `syl`, `char`, `style`, `metadata`.

## See Also

- [Types](./types.md)
- [Modifiers](./modifiers.md)
