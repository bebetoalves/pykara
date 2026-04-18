# coord

Helpers for ASS coordinates.

## `coord.round(value)`

Round one coordinate the same way ASS rendering normally quantizes it.

```ass
{\pos(!coord.round($syl_center + 0.5)!,$syl_middle)}
```

## See Also

- [shape](./shape.md)
