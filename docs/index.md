# Pykara Documentation

**Pykara** is a karaoke templating framework written in Python. It is conceptually inspired by the legacy Kara Templater
from Aegisub (originally implemented in Lua).

## Installation

Using `pipx` (recommended for isolated CLI tools):

```sh
pipx install .
```

Alternatively, for development or local usage:

```sh
pip install .
```

## Command-Line Usage

```sh
pykara input.ass output.ass
pykara input.ass output.ass --json output.json
pykara input.ass output.ass --warn-only
pykara input.ass output.ass --seed 42
pykara input.ass output.ass --font-dir ./fonts
```

| Flag | Description |
|------|-------------|
| `input` | Source `.ass` file. |
| `output` | Destination `.ass` file. |
| `--json PATH` | Also write generated events as JSON. |
| `--warn-only` | Demote validation errors to warnings and continue. |
| `--seed N` | Initial deterministic RNG seed. |
| `--font-dir PATH` | Prefer fonts from a directory before user/system fonts. Can be repeated. |

## Documentation

### Directives

- [Types](./directives/types.md) — Template, mixin, and code directives.
- [Scopes](./directives/scopes.md) — Setup, line, word, syllable, and character scopes.
- [Variables](./directives/variables.md) — Complete `$variable` reference.
- [Objects](./directives/objects.md) — Properties available in `!expr!`.
- [Modifiers](./directives/modifiers.md) — Directive modifier keywords.

### Scopes

- [Setup Scope](./directives/setup-scope.md) — One-time setup before any karaoke line runs.
- [Line Scope](./directives/line-scope.md) — One execution per karaoke line.
- [Word Scope](./directives/word-scope.md) — One execution per visible word.
- [Syllable Scope](./directives/syllable-scope.md) — One execution per karaoke syllable.
- [Char Scope](./directives/char-scope.md) — One execution per character inside a syllable.

### Tools

- [retime](./tools/retime.md) — Choose source timing for generated lines.
- [layer](./tools/layer.md) — Change generated line layers while rendering.
- [color](./tools/color.md) — Build ASS colors, alpha values, and blends.
- [global](./tools/global.md) — Share temporary values between templates and mixins.
- [coord](./tools/coord.md) — Round coordinates or calculate screen-space offsets.
- [shape](./tools/shape.md) — Move, rotate, center, or generate ASS drawings.
- [math](./tools/math.md) — Run numeric calculations inside `!expr!` and code.
- [random](./tools/random.md) — Add pseudo-random variation to generated lines.

### Bridges

- [Bridges](./bridges.md) — Use Pykara from editors and external tools.

## License

Distributed under the MIT License.
