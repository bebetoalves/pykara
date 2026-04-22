# global

Global functions are called directly, without a namespace. Use them in
templates and mixins while rendering karaoke lines.

## Available Functions

### `set(key, value)`

Store `value` under `key` and return `value`.

If the key already exists, the old value is replaced. `set` cannot change
a locked key.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\1c!set("main", color.rgb_to_ass(255, 200, 0))!}
```

### `lock(key, value)`

Save `value`, lock `key`, and return the stored value.

The first `lock` call for a new key saves its value. Later `lock` calls
with the same key keep returning the locked value. `set` cannot change a
locked key.

If the key already has an unlocked value, `lock` locks and returns that
current value.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template line,{\1c!lock("main", color.rgb_to_ass(255, 200, 0))!}
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,mixin line,{\3c!get("main")!}
```

Python still evaluates `value` each time the expression runs. `lock`
keeps the stored value fixed.

### `get(key, default_value=None)`

Return the value stored under `key`. If the key does not exist, return
`default_value`.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\1c!get("main")!}
```

## Scope Behavior

`get` and `set` use one shared store for the current render.

The store is not split by scope. A value set in a `line`, `word`, `syl`,
`char`, or mixin template can be read later by another template or mixin.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\1c!set("main", color.rgb_to_ass(255, 200, 0))!}
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\1c!get("main")!}
```

The latest `set` wins unless the key is locked:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,!set("index", syl.i)!
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,!get("index")!
```

The value remains available until another `set` uses the same key. It is
not cleared when Pykara moves to the next syllable, word, or line.

Use a default value when the key may not exist yet:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\1c!get("main", style.primary_color)!}
```

## Notes

`get`, `set`, and `lock` are available in `template` and `mixin`. They
are not available in `code`; use normal Python variables there.

`set` and `lock` cannot store functions or methods.

Inside `!expr!`, `set` prints the value it stores:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\fscx!set("size", 120)!\fscy!get("size")!}
```

If `get` returns `None` inside `!expr!`, it prints nothing.

Values assigned inside `code` blocks do not use this store. They are
normal variables and are available as `$name` and `!name!` in later
template and mixin bodies.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code setup,main = color.rgb_to_ass(255, 200, 0)
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\1c$main}
```
