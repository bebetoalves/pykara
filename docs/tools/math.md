# math

Use `math` for numeric calculations inside `!expr!` and `code`
directives.

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

## Example

```ass
{\frz!math.sin($syl_i) * 10!}
```
