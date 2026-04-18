# Tools

Tools are runtime helpers available inside template expressions
(`!expr!`) and, unless noted otherwise, inside `code` directives.

## Available Tools

| Tool | Description |
|---------------------------------|----------------------------------|
| [`retime`](./tools/retime.md) | Choose which source timing range a generated line uses. |
| [`layer`](./tools/layer.md) | Change the generated line layer while rendering. |
| [`color`](./tools/color.md) | Build ASS colors, alpha values, and color blends. |
| [`coord`](./tools/coord.md) | Round coordinates or calculate screen-space offsets. |
| [`shape`](./tools/shape.md) | Move, rotate, center, or generate ASS drawing shapes. |
| [`global`](./tools/global.md) | Share temporary values between templates and scoped code. |
| [`math`](./tools/math.md) | Run numeric calculations inside `!expr!` and code. |
| [`random`](./tools/random.md) | Add pseudo-random variation to generated lines. |
