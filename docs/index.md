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
```

| Flag | Description |
|------|-------------|
| `input` | Source `.ass` file. |
| `output` | Destination `.ass` file. |
| `--json PATH` | Also write generated events as JSON. |
| `--warn-only` | Demote validation errors to warnings and continue. |
| `--seed N` | Deterministic RNG seed. |

## Documentation

### Directives

- [Types](./directives/types.md) — Template and code directives.
- [Scopes](./directives/scopes.md) — Init, line, word, syllable, and character scopes.
- [Variables](./directives/variables.md) — Complete `$variable` reference.
- [Objects](./directives/objects.md) — Properties available in `!expressions!`.
- [Modifiers](./directives/modifiers.md) — Template modifier keywords.

### Scopes

- [Init Scope](./directives/init-scope.md) — One-time setup before any karaoke line runs.
- [Line Scope](./directives/line-scope.md) — One execution per karaoke line.
- [Word Scope](./directives/word-scope.md) — One execution per visible word.
- [Syllable Scope](./directives/syllable-scope.md) — One execution per karaoke syllable.
- [Char Scope](./directives/char-scope.md) — One execution per character inside a syllable.

### Tools

- [retime](./tools/retime.md) — Retiming targets and presets for generated lines.
- [layer](./tools/layer.md) — Layer helpers for generated lines.
- [color](./tools/color.md) — Color conversion and interpolation helpers.
- [global](./tools/global.md) — Shared non-namespaced helper functions.
- [coord](./tools/coord.md) — Coordinate helpers for ASS rendering.
- [shape](./tools/shape.md) — ASS drawing shape helpers.
- [math](./tools/math.md) — Selected math helpers available at runtime.
- [random](./tools/random.md) — Seeded pseudo-random helpers.

## License

Distributed under the MIT License.
