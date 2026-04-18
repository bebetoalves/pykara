# Directive Types

Directives define an execution context for karaoke effects. The first
token of the `Effect` field chooses the directive type.

## `template`

Declares a template body. Each execution renders ASS override tags,
plain text, `$variables`, and `!expr!` into a generated line.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\pos($syl_center,$syl_middle)}
```

## `code`

Runs Python code. Values assigned here become available to later
directives as `!name!`.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code setup,main = color.rgb_to_ass(255, 128, 0)
```

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\1c!main!}
```
