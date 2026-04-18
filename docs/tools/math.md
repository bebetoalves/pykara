# math

A selected subset of Python's `math` module is available.

## Available Functions

### `math.floor(x)`

Round down.

### `math.ceil(x)`

Round up.

### `math.fabs(x)`

Return the absolute value as a float.

### `math.sqrt(x)`

Return the square root.

### `math.sin(x)`

Return the sine of `x`, in radians.

### `math.cos(x)`

Return the cosine of `x`, in radians.

### `math.radians(x)`

Convert degrees to radians.

### `math.polar(angle, radius, axis=None)`

Return screen-space polar coordinates.

## Example

```ass
{\frz!math.sin($syl_i) * 10!}
{\pos(!$syl_center + math.polar(45, 30, "x")!,$syl_middle)}
```
