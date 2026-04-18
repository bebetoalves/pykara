# math

A selected subset of Python's `math` module is available.

## Available Functions

| Name | Description |
|------|-------------|
| `math.floor(x)` | Round down. |
| `math.ceil(x)` | Round up. |
| `math.fabs(x)` | Absolute value as a float. |
| `math.sqrt(x)` | Square root. |
| `math.sin(x)` | Sine (radians). |
| `math.cos(x)` | Cosine (radians). |
| `math.radians(x)` | Degrees to radians. |
| `math.polar(angle, radius, axis=None)` | Screen-space polar coordinates. |

## Example

```ass
{\frz!math.sin($syl_i) * 10!}
{\pos(!$syl_center + math.polar(45, 30, "x")!,$syl_middle)}
```

## See Also

- [random](./random.md)
