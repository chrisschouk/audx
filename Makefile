.PHONY: dev test lint format build publish-npm publish-py

dev:
	python3 -m venv .venv || true
	.venv/bin/python -m pip install -e .[dev]
	@echo "✓ Development environment ready in .venv"
	@echo "Note: On macOS, install PortAudio via: brew install portaudio"
	@echo "      On Linux, install PortAudio via: sudo apt install libportaudio2"

test:
	uv run pytest -q

lint:
	uv run ruff check src tests
	uv run mypy src/audx

format:
	uv run ruff format src tests

build:
	uv build

publish-npm:
	npm publish

publish-py:
	uv publish
