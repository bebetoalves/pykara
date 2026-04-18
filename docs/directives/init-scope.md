# Init Scope

The `init` scope runs once, before any karaoke line is processed. Only
`code` directives may target it.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code init,main = color.ass(255, 128, 0)
```

## Purpose

- Pre-compute values every line will use.
- Store palettes or other shared data.

## What's Available

- Color builders: `color.ass`, `color.alpha`, `color.interpolate`.
- Shared store: `set`, `get`.
- Modules: `math`, `random`.

Line, syllable, and character variables are **not** available here.

## Example

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code init,main = color.ass(255, 200, 0)
```

Then reference it in a template:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\1c!main!}
```

## See Also

- [Types](./types.md)
- [store](../tools/store.md)
