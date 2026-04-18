# color

Helpers for building and interpolating ASS colors.

## Available Functions

### `color.rgb_to_ass(r, g, b)`

Return an ASS color string. Components are clamped to `[0, 255]`.

```ass
{\1c!color.rgb_to_ass(255, 128, 0)!}
```

### `color.alpha(a)`

Return an ASS alpha string. `a` is clamped to `[0, 255]`.

```ass
{\alpha!color.alpha(128)!}
```

### `color.interpolate(t, c1, c2)`

Interpolate between two ASS colors at `t ∈ [0, 1]`. Inputs may be ASS
colors, ASS alphas, or HTML hex strings like `#FF8000`.

```ass
{\1c!color.interpolate(0.5, "&H000000FF&", "&H0000FF00&")!}
```
