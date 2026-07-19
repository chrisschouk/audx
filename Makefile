.PHONY: test lint format build publish-npm publish-py

test:
	uv run pytest -q

lint:
	uv run ruff check src tests
	uv run mypy src/audx

format:
	uv run ruff check --fix src tests

build:
	uv build

publish-npm:
	npm publish

publish-py:
	twine upload dist/*
