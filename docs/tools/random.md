# random

A selected subset of Python's `random` module is available. Output is
deterministic when `--seed` is passed to the CLI.

## Available Functions

| Name | Description |
|------|-------------|
| `random.random()` | Uniform float in `[0.0, 1.0)`. |
| `random.randint(a, b)` | Uniform int with `a <= N <= b`. |

## Example

```ass
{\frz!random.randint(-5, 5)!}
```

## Determinism

```sh
pykara input.ass output.ass --seed 42
```

## See Also

- [math](./math.md)
