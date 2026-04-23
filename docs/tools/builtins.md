# Built-in Functions

Pykara exposes a small allowlist of Python built-in functions inside
template expressions (`!expr!`), mixins, and `code` directives.

These names are available directly, without a namespace:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,!sum(range(4))!
```

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code setup,steps = list(range(4))
```

## Available Functions

| Function | Description |
|--------------------------|----------------------------------------------|
| `abs(value)` | Return the absolute value. |
| `all(iterable)` | Return `True` when every item is truthy. |
| `any(iterable)` | Return `True` when at least one item is truthy. |
| `bool(value)` | Convert a value to `True` or `False`. |
| `dict(...)` | Build a dictionary. |
| `enumerate(iterable)` | Iterate as `(index, value)` pairs. |
| `float(value)` | Convert a value to a float. |
| `int(value)` | Convert a value to an integer. |
| `len(value)` | Return the length of a sequence or collection. |
| `list(iterable)` | Build a list. |
| `max(...)` | Return the largest value. |
| `min(...)` | Return the smallest value. |
| `range(...)` | Build an integer range for loops and comprehensions. |
| `reversed(sequence)` | Iterate over a sequence in reverse order. |
| `round(value, ndigits=None)` | Round a numeric value. |
| `set(iterable=())` | Build a set. |
| `sorted(iterable)` | Return a sorted list. |
| `str(value)` | Convert a value to text. |
| `sum(iterable)` | Add numeric values. |
| `tuple(iterable)` | Build a tuple. |
| `zip(...)` | Iterate over multiple iterables in parallel. |

## Examples

Use `range` and `sum` directly in a template expression:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,!sum(range(syl.i + 1))!
```

Build lists in setup code:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code setup,offsets = list(range(0, 120, 20))
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\pos(!$syl_center + offsets[$syl_i % len(offsets)]!,$syl_middle)}
```

Use `enumerate` or `zip` in code helpers:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code setup,pairs = list(zip(range(3), reversed(range(3))))
```

## Notes

For Pykara's shared store helpers, see [`global`](./global.md) for
`get`, `put`, and `lock`.

Unsafe or environment-facing built-ins such as `open`, `eval`, `exec`,
`compile`, `globals`, `locals`, `vars`, `dir`, `getattr`, `setattr`,
`delattr`, `type`, `object`, `super`, `input`, `print`, and `help` are
not exposed.

Python `import` is also not exposed. Use the documented namespaces such
as [`math`](./math.md), [`random`](./random.md), [`color`](./color.md),
[`coord`](./coord.md), and [`shape`](./shape.md).
