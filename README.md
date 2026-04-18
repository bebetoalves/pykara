# Pykara Templater

Pykara generates karaoke effect (`fx`) lines for ASS subtitle files.

## Requirements

- Python 3.11+
- [pysubs2](https://github.com/tkarabela/pysubs2) >= 1.7

## Installation

```sh
pipx install .
```

## Usage

```sh
pykara input.ass output.ass
pykara input.ass output.ass --json output.json
pykara input.ass output.ass --warn-only
pykara input.ass output.ass --seed 42
```

## Development

```sh
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run checks:

```sh
mdformat --check .
ruff check pykara tests
ruff format --check pykara tests
pyright
pytest --cov
```

## License

MIT
