# retime

Retime the generated line with an explicit target.

## Usage

```python
retime.<target>()
retime.<target>(start_offset, end_offset)
retime.<target>.<preset>(start_offset, end_offset)
```

Call `retime` at the start of a template body to change the generated
line's timing. Offsets are milliseconds: negative values move that edge
earlier, positive values move it later, and omitted offsets default to
`0`.

Each template evaluation accepts at most one `retime` call.

## Timeline

```text
  0                  s0              s1                D
  |                  |               |                 |
  +------------------+---------------+-----------------+
  ^                  ^               ^                 ^
  preline            presyl          postsyl           postline

  |<----------------------- line ---------------------->|

  |<---- start2syl ---->|

                     |<------ syl ------>|

                                       |<-- syl2end -->|
```

## Available Functions

### Targets

| Target | Result range |
|-------------|---------------------------------|
| `line` | Full source line. |
| `preline` | Line start anchor. |
| `postline` | Line end anchor. |
| `syl` | Syllable start to syllable end. |
| `presyl` | Syllable start anchor. |
| `postsyl` | Syllable end anchor. |
| `start2syl` | Line start to syllable start. |
| `syl2end` | Syllable end to line end. |

`line`, `preline`, and `postline` are valid in `template line`,
`template word`, `template syl`, and `template char`.

`syl`, `presyl`, and `postsyl` are valid in `template syl` and
`template char`. In `template char`, the active syllable is the
character's parent syllable.

`start2syl` and `syl2end` are valid only in `template syl`.

### Presets

Presets apply a stagger to each item in the current scope: words in
`template word`, syllables in `template syl`, and characters in
`template char`.

Use line targets (`line`, `preline`, `postline`) to stagger across the
whole line. Use syllable targets (`syl`, `presyl`, `postsyl`,
`start2syl`, `syl2end`) only when the template has an active syllable.

Presets are invalid in `template line`. Preset collections with zero or
one element are runtime errors.

Available presets:

| Preset | Order |
|---------------|-----------------------------|
| `ltr` | textual left to right |
| `rtl` | textual right to left |
| `from_center` | center first |
| `from_edges` | edges first |
| `odd_first` | odd indexes first |
| `even_first` | even indexes first |
| `spatial_ltr` | visual left to right |
| `spatial_rtl` | visual right to left |
| `random` | deterministic pseudo-random |

## Examples

Play a fade-in right before each syllable:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,!retime.presyl(0, 200)!{\pos($syl_center,$syl_middle)\fad(200,0)}
```

Fade each syllable out after it finishes:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,!retime.syl2end()!{\pos($syl_center,$syl_middle)\t(\alpha&HFF&)}
```

Stagger line lead-in across characters:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template char,!retime.line.ltr(-300, 0)!{\pos($char_center,$char_middle)\fad(300,0)}
```
