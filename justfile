PYTHON := "./.venv/bin/python"

init:
	uv sync --extra dev

fetch:
	{{PYTHON}} -m invest_notify.main fetch

plot:
	{{PYTHON}} -m invest_notify.main plot

notify:
	{{PYTHON}} -m invest_notify.main notify

run:
	{{PYTHON}} -m invest_notify.main run-scheduler

test:
	uv run pytest -q

lint:
	uv run ruff check .

format:
	uv run ruff check . --fix
