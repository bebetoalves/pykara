# Objects

Inside `!expr!`, runtime data is exposed through objects.

## Available Objects

### `line`

| Property | Description |
|----------|-------------|
| `layer` | Output layer. |
| `actor` | Output actor. |
| `raw_text` | Original line text, including tags. |
| `text` | Visible line text. |
| `trimmed_text` | Visible line text without outer whitespace. |
| `start` | Start time in ms. |
| `end` | End time in ms. |
| `dur` | Duration in ms. |
| `mid` | Midpoint in ms. |
| `i` | Karaoke line index. |
| `left` | Left edge. |
| `center` | Horizontal center. |
| `right` | Right edge. |
| `width` | Width. |
| `top` | Top edge. |
| `middle` | Vertical center. |
| `bottom` | Bottom edge. |
| `height` | Height. |
| `x` | ASS anchor x position. |
| `y` | ASS anchor y position. |
| `syls` | Read-only sequence of syllables. |

### `word`

| Property | Description |
|----------|-------------|
| `text` | Visible word text. |
| `trimmed_text` | Word text without outer whitespace. |
| `start` | Start time in ms. |
| `end` | End time in ms. |
| `dur` | Duration in ms. |
| `kdur` | Duration in centiseconds. |
| `mid` | Midpoint in ms. |
| `n` | Total word count in the line. |
| `i` | Word index. |
| `left` | Left edge. |
| `center` | Horizontal center. |
| `right` | Right edge. |
| `width` | Width. |
| `top` | Top edge. |
| `middle` | Vertical center. |
| `bottom` | Bottom edge. |
| `height` | Height. |
| `x` | ASS anchor x position. |
| `y` | ASS anchor y position. |

### `syl`

| Property | Description |
|----------|-------------|
| `text` | Visible syllable text. |
| `trimmed_text` | Syllable text without outer whitespace. |
| `start` | Start time in ms. |
| `end` | End time in ms. |
| `dur` | Duration in ms. |
| `kdur` | Duration in centiseconds. |
| `mid` | Midpoint in ms. |
| `n` | Total syllable count in the line. |
| `i` | Syllable index. |
| `left` | Left edge. |
| `center` | Horizontal center. |
| `right` | Right edge. |
| `width` | Width. |
| `top` | Top edge. |
| `middle` | Vertical center. |
| `bottom` | Bottom edge. |
| `height` | Height. |
| `x` | ASS anchor x position. |
| `y` | ASS anchor y position. |
| `tag` | Source karaoke tag such as `\k20`. |
| `inline_fx` | Parsed inline-fx marker. |

### `char`

| Property | Description |
|----------|-------------|
| `text` | Visible character text. |
| `trimmed_text` | Character text without outer whitespace. |
| `i` | Character index in the syllable. |
| `n` | Total character count in the syllable. |
| `left` | Left edge. |
| `center` | Horizontal center. |
| `right` | Right edge. |
| `width` | Width. |
| `top` | Top edge. |
| `middle` | Vertical center. |
| `bottom` | Bottom edge. |
| `height` | Height. |
| `x` | ASS anchor x position. |
| `y` | ASS anchor y position. |

### `style`

| Property | Description |
|----------|-------------|
| `name` | Style name. |
| `primary_color` | Style primary color in ASS format. |
| `secondary_color` | Style secondary color in ASS format. |
| `outline_color` | Style outline color in ASS format. |
| `shadow_color` | Style shadow color in ASS format. |
| `outline` | Outline width. |

### `metadata`

| Property | Description |
|----------|-------------|
| `res_x` | Script resolution width. |
| `res_y` | Script resolution height. |

### `palette`

Tailwind color palette exposed as ASS colors. Choose a color and shade:

```ass
{\1c!palette.red[500]!}
```

Available colors:

`slate`, `gray`, `zinc`, `neutral`, `stone`, `red`, `orange`, `amber`,
`yellow`, `lime`, `green`, `emerald`, `teal`, `cyan`, `sky`, `blue`,
`indigo`, `violet`, `purple`, `fuchsia`, `pink`, `rose`.

Available shades:

`50`, `100`, `200`, `300`, `400`, `500`, `600`, `700`, `800`, `900`, `950`.
