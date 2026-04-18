# shape

Use `shape` to move, rotate, center, or generate ASS drawing shapes for
`\p` drawings and clipping masks.

## Available Functions

### `shape.rotate(shape, angle, origin_x=0, origin_y=0)`

Rotate every point in a drawing shape around an origin.

```ass
{\p1}!shape.rotate("m 0 0 l 10 0", 90)!{\p0}
```

### `shape.center_at(shape, x=0, y=0)`

Move a shape so its bounding-box center sits at `x,y`.

```ass
{\p1}!shape.center_at("m 0 0 l 10 20", $syl_center, $syl_middle)!{\p0}
```

### `shape.displace(shape, offset_x, offset_y)`

Move every point in a drawing shape by `offset_x,offset_y`.

```ass
{\p1}!shape.displace("m 0 0 l 10 0", 5, 8)!{\p0}
```

### `shape.split_clip(width, angle=0, x=0, y=0, height=None)`

Build a rotated split clipping shape centered at `x,y`.

```ass
{\clip(!shape.split_clip(syl.width, 0, syl.center, syl.middle)!)}
```
