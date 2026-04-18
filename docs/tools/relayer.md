# relayer

Set the output layer on the generated line.

```python
relayer(layer)
```

Returns an empty string.

## Example

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,!relayer(2)!{\pos($syl_center,$syl_middle)}
```

Higher layers are drawn on top of lower ones. Use separate layers to
keep fills, outlines, and shadows from interfering.

## See Also

- [Modifiers](../directives/modifiers.md)
