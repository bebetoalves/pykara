# Interpolation

Template bodies support two forms of substitution:

| Form | Meaning |
|------|---------|
| `$name` | Substitute the value of a variable. |
| `!expr!` | Evaluate an expression and substitute the result. |

## Variable Substitution — `$name`

```ass
template syl,{\pos($syl_center,$syl_middle)}
```

The name is looked up among the current scope's variables (see
[Scopes](./scopes.md)) and any values set by `code` directives.

## Expression Evaluation — `!expr!`

```ass
template syl,{\frz!$syl_i * 10!}
```

Expressions may use any variable, any [tool](../tools.md), and the
`math` / `random` modules.

## Object-Style Access

Expressions can also read data through objects:

```
!syl.center!
!line.dur!
!style.primary_color!
```

See [Scopes](./scopes.md) for the full list.

## Order of Evaluation

1. All `$name` tokens are replaced.
1. Then all `!expr!` blocks are evaluated.

## See Also

- [Types](./types.md)
- [Scopes](./scopes.md)
- [Tools](../tools.md)
