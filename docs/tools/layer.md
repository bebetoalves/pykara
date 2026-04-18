# layer

Helpers for changing generated line layers.

## Available Functions

### `layer.set(value)`

Set the layer of the generated line. Returns `None`, so inside template
text it renders as an empty string.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,!layer.set(2)!{\pos($syl_center,$syl_middle)}
```
