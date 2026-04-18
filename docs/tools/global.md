# global

Functions without a namespace that are available in both `code` and
`template` contexts.

## Available Functions

### `set(key, value)`

Store `value` under `key` and return it.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code init,set("main", color.rgb_to_ass(255, 200, 0))
```

### `get(key, default_value=None)`

Return the value stored under `key`, or `default_value` when the key is
missing.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\1c!get("main")!}
```

## Notes

Values assigned inside `code` blocks are available as `!name!`, but not
as `$name`.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code init,main = color.rgb_to_ass(255, 200, 0)
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\1c!main!}
```
