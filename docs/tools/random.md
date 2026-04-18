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

Without `--seed`, Pykara uses a fresh pseudo-random sequence for each run.
With `--seed`, every call is still random-like, but the sequence is
repeatable for the same input and seed.

```sh
pykara input.ass output.ass --seed 42
```
