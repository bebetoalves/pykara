# store

Persist values across directives using a shared key-value store.

## `set(key, value)`

Store `value` under `key`. Returns `value`.

## `get(key, default_value=None)`

Return the value previously stored, or `default_value` if the key is
missing.

## Example

Save a palette once, reuse it per syllable:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code init,set("main", color.ass(255, 200, 0))
```

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\1c!get("main")!}
```

## When to Use Assignments Instead

For simple values, a plain assignment inside a `code` block is enough:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code init,main = color.ass(255, 200, 0)
```

Then reference `$main` or `!main!` from templates.

## See Also

- [Init Scope](../directives/init-scope.md)
- [Code directive](../directives/types.md)
