# Contributing to audx

audx is a local-first terminal and browser music tool. The goal is a usable, magical workflow: scan your hard drive, write patterns, jam live, render WAVs, export to Ableton Live Sets (`.als`), and keep the project file clean.

## Local Setup

### macOS / Linux Venv Setup
```bash
make dev
# or manually:
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .[dev]

# Native audio drivers
brew install portaudio            # macOS
# or: sudo apt install libportaudio2  # Linux
```

## Maintainer Sanity Check

Run this baseline suite to verify the CLI before opening a PR:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .

audx doctor
audx midi list
audx jam --once
audx open --help
```

## Checks

Run these before opening a pull request:

```bash
uv run pytest -q
uv run ruff check src tests
uv run mypy src/audx
uv build
```

## Development Principles

- Keep the `.audx` file as the source of truth with atomic writes.
- Prefer local/offline behaviour with zero-config synthetic audio fallbacks.
- Add tests for new CLI subcommands and audio behavior before implementation.
- Keep CLI output scriptable, beautiful, and calm.
