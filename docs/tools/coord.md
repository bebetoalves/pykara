# coord

Use `coord` when a position calculation needs ASS-style rounding or a
screen-space offset from an angle and distance.

## Available Functions

### `coord.round(value)`

Round one coordinate the same way ASS rendering normally quantizes it.

```ass
{\pos(!coord.round($syl_center + 0.5)!,$syl_middle)}
```

### `coord.polar(angle, radius, axis=None)`

Return an offset from an angle and radius using ASS screen coordinates.
Positive Y points downward, so positive angles move upward. Pass `"x"` or
`"y"` as `axis` to return only one component.

```ass
{\pos(!$syl_center + coord.polar(45, 30, "x")!,$syl_middle)}
```
