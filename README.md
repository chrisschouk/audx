# audx

A terminal-native digital audio workstation for pattern sequencing, live-coded sample playback, and Ableton session export. Built for a calm, local, hackable workflow with zero cloud dependency.

## ⚡ 10-Second Quickstart

```bash
# 1. Install audx in a virtual environment
python3 -m venv .venv
source .venv/bin/activate
python -m pip install audx

# Native audio drivers
brew install portaudio               # macOS
# or: sudo apt install libportaudio2   # Linux

# 2. Sanity check & hard drive sample scan
audx doctor
audx samples scan

# 3. Jam instantly!
audx jam --genre techno
```

---

## 🎛 Primary User Journey

```bash
audx doctor                             # Diagnostics
audx samples scan                       # Auto-scan hard drive for audio samples
audx jam --genre house                  # Instant live jam on the spot
audx open my-track                      # Open terminal DAW TUI
audx open my-track --web                # Open Web companion on http://localhost:8080/app
audx export als my-track/project.audx   # Export to native Ableton Live Set (.als)
audx song render my-track/project.audx  # Render project to WAV
```

---

## 💻 Commands

```bash
audx doctor                             # Run diagnostics (PortAudio, MIDI, CLI stack)
audx jam [--genre techno|house|hiphop]  # Live interactive jam session (with synth audio fallbacks)
audx jam --chromatic                    # Pitched chromatic synth keyboard mode
audx samples scan                       # Auto-scan ~/Music, ~/Downloads, ~/Samples for audio files
audx init <name>                        # Scaffold project folder (stems/, renders/, git init)
audx open [project] [--web]             # Open terminal TUI or Web browser companion
audx push2 lights                       # Test Push 2 pad LED lighting matrix grid
audx push2 map                          # Print Push 2 MIDI mapping scaffold
audx midi list                          # List MIDI input and output ports
audx midi out "Push 2"                  # Send 24 PPQN MIDI clock sync
audx midi rec <name> --bars 1           # Record incoming MIDI as a pattern
audx export als project.audx            # Export project to native Ableton Live Set (.als)
audx export midi out.mid                # Export patterns to Standard MIDI File
audx song render project.audx           # Render a saved project to WAV
audx render-project project.audx        # Alias for song render
audx pattern create <name> "<dsl>"      # Parse/check a pattern
audx pattern set <ch> "<dsl>"           # Replace a channel's DSL line
audx pattern step <ch> <n> [on|off]     # Toggle/set one step in a channel grid
audx pattern list                       # List patterns in current process
audx load sample.wav --ch 0 --project project.audx
                                        # Copy audio into stems/ and bind to channel
audx track add <name> "<dsl>" -c 2      # Add a track to the engine
audx track rm <name>                    # Remove a track
audx mix set <ch> gain <dB>             # Set channel gain
audx mix set <ch> mute on|off           # Set channel mute
audx mute <ch>                          # Toggle channel mute
audx stems search 909 kick              # Fuzzy-search the sample index
audx diff a.audx b.audx                 # Human-readable project diff
audx finish project.audx --profile ukg  # Render + master via sadact-finisher
audx fork project new-name              # Cheap branching
audx save beat.audx                     # Save current in-process state
audx load beat.audx                     # Load and print project state
audx projects list                      # List saved project files
audx watch project.audx                 # Hot-reload .audx on save
audx serve --port 8080                  # Monitor dashboard + /app playable browser UI
audx version                            # Print version
```

---

## 🛠 Troubleshooting

### `zsh: command not found: pip`
Use `python3 -m pip` or create a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install audx
```
Or install globally via `pipx` / `uv`:
```bash
pipx install audx
# or: uv tool install audx
```

### PEP 668 `externally-managed-environment`
Homebrew Python and macOS protect system packages. Always install inside a venv (`python3 -m venv .venv && source .venv/bin/activate`).

### `ModuleNotFoundError: No module named 'click'`
Re-install inside a fresh venv: `python -m pip install --force-reinstall audx`.

---

## 🎹 Pattern DSL

```bash
audx pattern create kick "kick 4/4"                          # four on the floor
audx pattern create snare "snare 2/8"                        # beats 2 and 4
audx pattern create hats "hh 16x8 | vel 0.45 | channel 2"    # 8 hats over 16 steps
audx pattern create groove "x--- -x-- --x- ---x"             # x/rest grid
audx pattern create perc "perc e(5,16,2)"                    # Euclidean, rotated
audx pattern create clap "clap [1.0.1.0.1.1.0.0]"            # explicit grid
```

---

## 🛠 Development

```bash
make dev
uv run pytest -q
uv run ruff check src tests
uv run mypy src/audx
```

---

## 💡 Philosophy

Code is the controller. Sound is the canvas. Terminal is the dimension.

Can Chris open a terminal, hit play, and feel like he is controlling a musical instrument rather than debugging Python? Yes.
