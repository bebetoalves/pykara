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

Code can reseed the same RNG by assigning `__seed__ = N`. The CLI seed initializes
the run first, then each `__seed__` assignment in any `code` scope controls later
`random` calls.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code setup,__seed__ = 7
```
