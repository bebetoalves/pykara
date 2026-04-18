# Pykara Documentation

Pykara generates karaoke effect (`fx`) lines for ASS subtitle files.

## Installation

```sh
pip install pykara-templater
```

## Command-Line Usage

```sh
pykara input.ass output.ass
pykara input.ass output.ass --json output.json
pykara input.ass output.ass --warn-only
pykara input.ass output.ass --seed 42
```

| Flag | Description |
|------|-------------|
| `input` | Source `.ass` file. |
| `output` | Destination `.ass` file. |
| `--json PATH` | Also write generated events as JSON. |
| `--warn-only` | Demote validation errors to warnings and continue. |
| `--seed N` | Deterministic RNG seed. |

## Quick Links

- **[Directives](./directives.md)** — The template directive system.
- **[Tools](./tools.md)** — Functions available inside templates.

## Documentation

### Directives

- [Types](./directives/types.md) — Template and code directives.
- [Scopes](./directives/scopes.md) — Init, line, word, syllable, and character scopes.
- [Modifiers](./directives/modifiers.md) — Template modifier keywords.
- [Interpolation](./directives/interpolation.md) — `$var` and `!expr!` syntax.

### Scopes

- [Init Scope](./directives/init-scope.md)
- [Line Scope](./directives/line-scope.md)
- [Word Scope](./directives/word-scope.md)
- [Syllable Scope](./directives/syllable-scope.md)
- [Char Scope](./directives/char-scope.md)

### Tools

- [retime](./tools/retime.md)
- [relayer](./tools/relayer.md)
- [color](./tools/color.md)
- [store](./tools/store.md)
- [math](./tools/math.md)
- [random](./tools/random.md)

## License

MIT.
