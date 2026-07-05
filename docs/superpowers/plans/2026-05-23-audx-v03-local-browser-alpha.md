# audx v0.3 Local + Browser Alpha Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make audx usable as a local-first alpha with real project stem loading, project rendering, terminal workflows, and a playable browser UI served locally.

**Architecture:** Keep Python as the canonical backend for `.audx` projects, CLI commands, offline render, and the terminal TUI. Add a browser surface through `audx serve` that reads project state from local HTTP endpoints and plays patterns client-side with Web Audio. Push 2 hardware integration is explicitly out of scope for this pass.

**Tech Stack:** Python 3.10+, Typer, Textual, NumPy, soundfile, sounddevice, standard-library HTTP server, vanilla HTML/CSS/JavaScript Web Audio.

---

### Task 1: Project Stem Loading Core

**Files:**
- Modify: `src/audx/project.py`
- Test: `tests/test_project.py`

- [ ] Add a failing test that loads an external WAV into a project, copies it to `stems/`, records mixer channel metadata, and creates a channel pattern that references the relative stem path.
- [ ] Implement `Project.add_stem(project_path, source, channel, name=None, copy=True)` using `shutil.copy2` and stable relative paths.
- [ ] Verify `uv run pytest tests/test_project.py -q`.

### Task 2: Project Rendering Core

**Files:**
- Modify: `src/audx/arrangement.py`
- Modify: `src/audx/cli.py`
- Test: `tests/test_arrangement.py`

- [ ] Add a failing test that renders a `.audx` project containing a stem-backed pattern to a stereo WAV.
- [ ] Implement `render_project(project_path, output_path, bars=None)` using the project folder as the sample library root.
- [ ] Add `audx render-project project.audx --output renders/name.wav`.
- [ ] Verify the new test and existing render tests.

### Task 3: Terminal Workflow Commands

**Files:**
- Modify: `src/audx/cli.py`
- Test: `tests/test_cli_spec_commands.py`

- [ ] Add failing tests for `audx load sample.wav --ch 3 --project project.audx` and `audx render-project`.
- [ ] Extend the existing `load` command so `--ch` means load a stem into a project; without `--ch` it keeps loading project files.
- [ ] Keep command output plain and scriptable.
- [ ] Verify CLI tests.

### Task 4: Browser Playable UI

**Files:**
- Modify: `src/audx/web.py`
- Test: `tests/test_batch_additions.py`

- [ ] Add failing tests for `/app`, `/api/project?path=...`, and `/api/audio?path=...`.
- [ ] Replace the read-only dashboard with a local browser instrument: mixer rows, pattern grid, transport, file input, and project JSON loading.
- [ ] Use Web Audio client-side for playback from browser-selected files and server-served local project audio files.
- [ ] Keep `/state` backwards compatible.
- [ ] Verify web tests.

### Task 5: Open Source Readiness

**Files:**
- Create: `LICENSE`
- Create: `CONTRIBUTING.md`
- Create: `SECURITY.md`
- Modify: `.github/workflows/ci.yml`
- Modify: `README.md`

- [ ] Add MIT licence text matching `pyproject.toml`.
- [ ] Add contributor instructions with local commands.
- [ ] Add security policy for local-only software.
- [ ] Update CI to run pytest, Ruff, mypy, and package build.
- [ ] Update README to describe terminal and browser modes honestly.

### Task 6: Final Verification

**Files:**
- No code files.

- [ ] Run `uv run pytest -q`.
- [ ] Run `uv run ruff check src tests`.
- [ ] Run `uv run mypy src/audx`.
- [ ] Run `uv build`.
- [ ] Run a TUI smoke test and a web endpoint smoke test.
- [ ] Summarise what is now complete and what remains out of scope.

