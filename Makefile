.PHONY: install fmt lint test

install:
	poetry install

fmt:
	poetry run ruff format .
	poetry run ruff check --fix .

lint:
	poetry run ruff check .
	poetry run mypy docs_agent

test:
	poetry run pytest -x -q
