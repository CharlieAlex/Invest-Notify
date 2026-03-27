PYTHON := "./.venv/bin/python"

init:
	uv sync --extra dev

fetch:
	{{PYTHON}} -m main fetch

plot:
	{{PYTHON}} -m main plot

notify:
	{{PYTHON}} -m main notify

test:
	uv run pytest -q

lint:
	uv run ruff check .

format:
	uv run ruff check . --fix
