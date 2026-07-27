# Getting Started with audx

`audx` is a terminal-native DAW for pattern sequencing, stem mixing, live-coded sample playback, and Ableton session export.

## Installation

### Recommended: Python Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install audx
```

### Alternative: Global Tool Install
```bash
pipx install audx
# or: uv tool install audx
```

### Native Audio Drivers
`audx` uses PortAudio for low-latency audio callbacks:
- **macOS**: `brew install portaudio`
- **Linux**: `sudo apt install libportaudio2`

---

## 5-Minute Quickstart

```bash
# 1. Run diagnostics
audx doctor

# 2. Auto-scan hard drive for audio samples
audx samples scan

# 3. Scaffold a new project
audx init my-beat

# 4. Jam live on the spot
audx jam --genre techno

# 5. Open project in terminal TUI or Web browser
audx open my-beat
audx open my-beat --web

# 6. Render WAV or export to Ableton Live Set (.als)
audx song render my-beat/project.audx --output my-beat/renders/master.wav
audx export als my-beat/project.audx -o my-beat/session.als
```

---

## Command Reference

| Command | Description |
|---|---|
| `audx doctor` | Run system diagnostics & check PortAudio/MIDI setup |
| `audx jam` | Start interactive live jam session |
| `audx jam --genre <genre>` | Auto-generate track (`techno`, `house`, `hiphop`, `ukg`, `ambient`) |
| `audx samples scan` | Auto-scan hard drive for `.wav`/`.flac`/`.mp3` audio files |
| `audx open [project]` | Open terminal TUI on project file or directory |
| `audx open --web` | Serve local Web Audio app on `http://localhost:8080/app` |
| `audx song render <proj>` | Render project to WAV |
| `audx export als <proj>` | Export project to native Ableton Live Set (`.als`) |
| `audx push2 lights` | Test Push 2 LED pad lighting matrix |
| `audx midi list` | List available MIDI input and output ports |
