# coord

Helpers for ASS coordinates, including rounding and screen-space movement.

## Available Functions

### `coord.round(value)`

Round one coordinate the same way ASS rendering normally quantizes it.

```ass
{\pos(!coord.round($syl_center + 0.5)!,$syl_middle)}
```

### `coord.polar(angle, radius, axis=None)`

Return an offset from an angle and radius using screen coordinates, where
positive Y points downward. Pass `"x"` or `"y"` as `axis` to return only
one component.

```ass
{\pos(!$syl_center + coord.polar(45, 30, "x")!,$syl_middle)}
```
