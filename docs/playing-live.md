# Playing audx live with a MIDI controller, Push 2, or Terminal

## ⚡ The 10-Second Jam

Get sound coming out of your speakers or pads in under 10 seconds:

```bash
# 1. Install audx in a clean virtual environment
python3 -m venv .venv
source .venv/bin/activate
python -m pip install audx

# Native audio drivers
brew install portaudio               # macOS
# or: sudo apt install libportaudio2   # Linux

# 2. Sanity check
audx doctor
audx midi list

# 3. Jam!
audx jam                             # Instant drum pad session
audx jam --genre techno             # Auto-generated 128 BPM techno jam
audx jam --chromatic                # Pitched synth keyboard mode
```

---

## 🚀 Instant HD Sample Auto-Scanning & Track Generation

`audx` can automatically index usable sample libraries across your computer so you don't need to specify manual paths:

```bash
# Scan ~/Music, ~/Downloads, ~/Samples, ~/Documents for audio files
audx samples scan

# Jam on the spot using scanned local samples
audx jam --genre house
audx jam --genre hiphop
audx jam --genre ukg
```

Supported genres: `techno`, `house`, `hiphop`, `ukg`, `ambient`.

If no sample files are found on your hard drive, `audx` automatically uses built-in **synthesized fallback voices** (808 sub kick, noise snare, metallic hi-hat), guaranteeing instant sound on day one.

---

## 🎛 Push 2 LED Lighting Grid & Mapping

`audx` includes native Push 2 pad LED lighting grid diagnostics:

```bash
# Test Push 2 8x8 pad lighting grid
audx push2 lights

# Display Push 2 control mapping matrix
audx push2 map
```

---

## 🎹 Live MIDI Recording & Clock Output

Lock external hardware or Ableton Live to `audx` tempo:

```bash
# List connected MIDI hardware ports
audx midi list

# Send 24 PPQN MIDI Clock to an output device
audx midi out "Push 2"

# Capture live incoming MIDI as a pattern
audx midi rec my_pattern --bars 1 --ch 0
```

---

## 🎚 Ableton Live Session Export

Export your terminal creations directly to an Ableton Live Set (`.als`):

```bash
audx export als my-project.audx -o my-session.als
```

Double-click `my-session.als` to open your clips, tracks, and tempo inside Ableton Live.

---

## 🌐 Local Web Companion

Launch the playable browser instrument alongside the terminal DAW:

```bash
audx open --web
# or: audx serve --port 8080
```

Opens `http://127.0.0.1:8080/app` with interactive Web Audio pattern playback.

---

## 🛠 Troubleshooting Modern Python Environments

### 1. `zsh: command not found: pip`
Many macOS installs do not place `pip` directly on `PATH`. Use `python3 -m pip`:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install audx
```
Or install via `pipx` / `uv`:
```bash
pipx install audx
# or: uv tool install audx
```

### 2. PEP 668 `externally-managed-environment`
Homebrew Python and macOS block global `pip install` to protect system packages. Always create a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install audx
```

### 3. `ModuleNotFoundError: No module named 'click'`
`audx` explicitly declares `click>=8.0.0` in its package manifest. Re-install in a fresh venv:
```bash
python -m pip install --force-reinstall audx
```
