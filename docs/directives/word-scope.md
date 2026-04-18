# Word Scope

The `word` scope runs once per word inside every karaoke line. Words are
separated by spaces in the visible karaoke text. Both `template` and
`code` directives can target it.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template word,{\pos($word_center,$word_middle)}
```

## Variables

Only the `line_*` and `word_*` variables are available in `word` scope.
See [Scopes](./scopes.md).

## Behavior

- One generated line is emitted per word per iteration.
- The source word text is appended by default; use `no_text` to skip it.
- Combine with `no_blank` to skip empty words.
- Syllables and characters inside a word run after that word's
  directives.

## Examples

Position each word:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template word,{\pos($word_center,$word_middle)}
```

Assign a per-word value for syllable templates inside the same word:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code word,word_is_even = word.i % 2 == 0
```

## See Also

- [Line Scope](./line-scope.md)
- [Syllable Scope](./syllable-scope.md)
- [Modifiers](./modifiers.md)
