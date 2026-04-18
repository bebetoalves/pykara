PYTHON ?= python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python
PIP := $(VENV_PYTHON) -m pip

.PHONY: venv install test lint typecheck format-check check

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	$(PIP) install -e '.[dev]'

test:
	$(VENV)/bin/pytest -q

lint:
	$(VENV)/bin/ruff check

typecheck:
	$(VENV)/bin/pyright

format-check:
	$(VENV)/bin/mdformat --check .

check: lint typecheck format-check test
