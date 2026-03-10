PYTHON := ./.venv/bin/python

.PHONY: init fetch plot run test lint format

init:
	uv sync --extra dev

fetch:
	$(PYTHON) -m invest_notify.main fetch

plot:
	$(PYTHON) -m invest_notify.main plot

run:
	$(PYTHON) -m invest_notify.main run-scheduler

test:
	uv run pytest -q

lint:
	uv run ruff check .

format:
	uv run ruff check . --fix
