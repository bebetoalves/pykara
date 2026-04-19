# Pykara Templater

**Pykara** is a karaoke templating framework written in Python. It is conceptually inspired by the legacy Kara Templater
from Aegisub (originally implemented in Lua).

## Requirements

- Python 3.11 or higher

## Installation

Using `pipx` (recommended for isolated CLI tools):

```sh
pipx install .
```

Alternatively, for development or local usage:

```sh
pip install .
```

## Usage

Basic invocation:

```sh
pykara input.ass output.ass
```

Optional flags:

```sh
pykara input.ass output.ass --json output.json   # Export intermediate data
pykara input.ass output.ass --warn-only          # Downgrade errors to warnings
pykara input.ass output.ass --seed 42            # Deterministic output
pykara input.ass output.ass --font-dir ./fonts   # Prefer fonts from a directory
```

For comprehensive information about the engine, please refer to the complete documentation available [here](docs/index.md).

## Development

Create and activate a virtual environment:

```sh
python -m venv .venv
source .venv/bin/activate
```

Install development dependencies:

```sh
pip install -e ".[dev]"
```

### Code Quality & Testing

Run all checks:

```sh
mdformat --check .
ruff check pykara tests
ruff format --check pykara tests
pyright
pytest --cov
```

## License

Distributed under the MIT License.
