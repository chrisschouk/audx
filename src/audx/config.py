"""Configuration and constants.

Directory locations follow each platform's conventions instead of hardcoding
macOS paths, and every one can be overridden with an environment variable so
audx behaves predictably on headless boxes, CI, and containers. Nothing here
creates directories at import time — the code that writes into these paths
makes them on demand — so importing ``audx`` has no side effects on the disk.
"""
import os
import sys
from pathlib import Path
from typing import Final

_sudo_user = os.environ.get("SUDO_USER")
HOME: Final = Path(f"/Users/{_sudo_user}") if _sudo_user and Path(f"/Users/{_sudo_user}").exists() else Path.home()
CONFIG_DIR: Final = HOME / "Library" / "Application Support" / "audx"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _env_dir(var: str) -> Path | None:
    """Return an explicit override from ``var`` (``~`` expanded), if set."""
    value = os.getenv(var)
    return Path(value).expanduser() if value else None


def _config_dir(platform: str = sys.platform, os_name: str = os.name) -> Path:
    """Per-user config directory, following the host platform's convention.

    ``platform`` and ``os_name`` default to the live values but are injectable
    so the resolution logic can be tested without monkeypatching ``sys``.
    """
    if override := _env_dir("AUDX_CONFIG_DIR"):
        return override
    if platform == "darwin":
        return HOME / "Library" / "Application Support" / "audx"
    if os_name == "nt":
        base = os.getenv("APPDATA")
        return (Path(base) if base else HOME / "AppData" / "Roaming") / "audx"
    # Linux / other Unix → XDG Base Directory spec.
    xdg = os.getenv("XDG_CONFIG_HOME")
    return (Path(xdg) if xdg else HOME / ".config") / "audx"


def _projects_dir() -> Path:
    """Default directory for ``.audx`` projects."""
    if override := _env_dir("AUDX_PROJECTS_DIR"):
        return override
    return HOME / "Documents" / "audx"


def _samples_dir() -> Path:
    """Default sample library location."""
    if override := _env_dir("AUDX_SAMPLES_DIR"):
        return override
    return HOME / "Samples"


CONFIG_DIR: Final = _config_dir()
SAMPLES_DIR: Final = _samples_dir()
PROJECTS_DIR: Final = _projects_dir()

# Audio
SAMPLE_RATE: Final = 44100
CHANNELS: Final = 2
BLOCK_SIZE: Final = 512  # ~11ms @ 44.1k

# Mixer
CHANNELS_COUNT: Final = 16

# Pattern
DEFAULT_BPM: Final = 128

# Runtime BPM (overridable via AUDX_BPM env)
AUDX_BPM: Final = int(os.getenv("AUDX_BPM", str(DEFAULT_BPM)))
DEFAULT_PPQN: Final = 960  # pulses per quarter note (MIDI resolution)

# UI
THEME = {
    "primary": "#d4a574",    # warm amber (sink-inspired)
    "secondary": "#a8c087",  # sage green
    "accent": "#e8a6c2",     # muted pink
    "background": "#111111",
    "surface": "#1e1e1e",
    "text": "#e0e0e0",
    "text-muted": "#888888",
    "border": "#333333",
}
