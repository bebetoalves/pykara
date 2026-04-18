# random

A selected subset of Python's `random` module is available. Output is
deterministic when `--seed` is passed to the CLI.

## Available Functions

### `random.random()`

Return a uniform float in `[0.0, 1.0)`.

### `random.randint(min_value, max_value)`

Return a uniform integer `N` such that `min_value <= N <= max_value`.

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
