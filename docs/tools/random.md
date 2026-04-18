# random

Use `random` to add pseudo-random variation to generated lines, such as
jitter, color choices, or rotation.

## Available Functions

### `random.random()`

Return a uniform float in `[0.0, 1.0)`.

### `random.randint(a, b)`

Return a uniform integer `N` such that `a <= N <= b`.

## Example

```ass
{\frz!random.randint(-5, 5)!}
```

## Determinism

Use `--seed` when you want the same input to produce the same random
values every time. Without a seed, each run may produce different values.

```sh
pykara input.ass output.ass --seed 42
```
