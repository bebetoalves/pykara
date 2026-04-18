# Tools

Tools are helpers available inside template expressions (`!expr!`). Most are
also available inside `code` directives.

## Available Tools

| Tool | Description |
|------|-------------|
| [`retime`](./tools/retime.md) | Retime the generated line. |
| [`relayer`](./tools/relayer.md) | Change the output layer. |
| [`color`](./tools/color.md) | Build ASS colors and alphas. |
| [`coord`](./tools/coord.md) | Round ASS coordinates. |
| [`shape`](./tools/shape.md) | Transform ASS drawing shapes. |
| [`store`](./tools/store.md) | Persist values across templates. |
| [`math`](./tools/math.md) | Selected math functions. |
| [`random`](./tools/random.md) | Seeded random numbers. |

## Quick Reference

- `retime.<target>(start_offset=0, end_offset=0)` — see [targets](./tools/retime.md).
- `relayer(layer)` — set the output layer.
- `color.ass(r, g, b)` / `color.alpha(a)` — build ASS colors and alphas.
- `color.interpolate(t, c1, c2)` — blend two ASS colors.
- `coord.round(value)` — round one ASS coordinate.
- `shape.rotate`, `shape.centerpos`, `shape.displace`, `shape.slider`.
- `set(key, value)` / `get(key, default_value=None)` — shared store.
- `math.floor`, `math.ceil`, `math.fabs`, `math.sqrt`, `math.sin`, `math.cos`, `math.radians`, `math.polar`.
- `random.random`, `random.randint`.

## See Also

- [Directives](./directives.md)
- [Interpolation](./directives/interpolation.md)
