# Directive Types

Directives define an execution context for karaoke effects. The first
token of the `Effect` field chooses the directive type.

## `template`

Declares a template body. Each execution renders ASS override tags,
plain text, `$variables`, and `!expressions!` into a generated line.

- **Modifiers:** `loop`, `no_blank`, `no_text`, `fx`, `when`, `unless`.
- **Body:** ASS override tags, plain text, `$variables`, and `!expressions!`.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\pos($syl_center,$syl_middle)}
```

The source syllable text is appended to the rendered body unless
`no_text` is used.

## `code`

Runs Python code. Values assigned here become available to later
directives as `!name!`.

- **Modifiers:** none.
- **Runtime names:** expression objects such as `line`, `word`, `syl`,
  `style`, `metadata`, plus helpers like `color.*`, `math.*`, and other
  documented tools.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code setup,main = color.rgb_to_ass(255, 128, 0)
```

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\1c!main!}
```
