# Getting Started with audx

`audx` is a terminal-native DAW for pattern sequencing, stem mixing, live-coded sample playback, and Ableton session export.

**Prefer no install?** Open the [browser studio](https://audx-five.vercel.app/studio.html) or [pattern playground](https://audx-five.vercel.app/play.html).

## Installation

Install from GitHub (PyPI's `audx` package is a different unrelated project):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install "git+https://github.com/chrisschouk/audx.git"
```

### Native Audio Drivers (for live playback)

`audx` uses PortAudio for low-latency audio callbacks:
- **macOS**: `brew install portaudio`
- **Linux**: `sudo apt install libportaudio2`

Offline commands (`audx demo`, render, export) work without PortAudio.

---

## 5-Minute Quickstart

```bash
# 1. Run diagnostics
audx doctor

# 2. Offline proof — render a synth-kit demo beat
audx demo loop.wav

# 3. Optional: index local samples
audx samples scan

# 4. Scaffold a new project
audx init my-beat

# 5. Jam live (pads / Push 2); --genre loads a looping pattern pack
audx jam --genre techno

# 6. Open the terminal TUI (optional read-only dashboard)
audx open my-beat
audx open my-beat --serve

# 7. Render WAV or export to Ableton Live Set (.als)
audx song render my-beat/project.audx --output my-beat/renders/master.wav
audx export als my-beat/project.audx -o my-beat/session.als
```

---

## Command Reference

| Command | Description |
|---|---|
| `audx doctor` | Run system diagnostics & check PortAudio/MIDI setup |
| `audx demo` | Render a synth-kit demo beat (offline, no hardware) |
| `audx jam` | Start interactive live jam session |
| `audx jam --genre <genre>` | Load genre pattern pack (`techno`, `house`, `hiphop`, `ukg`, `ambient`) |
| `audx samples scan` | Auto-scan hard drive for `.wav`/`.flac`/`.mp3` audio files |
| `audx open [project]` | Open terminal TUI on project file or directory |
| `audx open --serve` | Also host the read-only live dashboard on port 8080 |
| `audx serve` | Read-only live monitor dashboard |
| `audx song render <proj>` | Render project to WAV |
| `audx export als <proj>` | Export project to native Ableton Live Set (`.als`) |
| `audx push2 lights` | Test Push 2 LED pad lighting matrix |
| `audx midi list` | List available MIDI input and output ports |
