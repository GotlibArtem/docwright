.PHONY: install fmt lint test

install:
	poetry install

fmt:
	poetry run ruff format .
	poetry run ruff check --fix .

lint:
	poetry run ruff check .
	poetry run mypy ai_docgen

test:
	poetry run pytest -x -q
