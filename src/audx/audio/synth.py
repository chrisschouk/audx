"""Synthesized fallback voices for zero-setup audio playback."""

from __future__ import annotations

from typing import Any, cast

import numpy as np

from audx.engine import Voice


def generate_synthetic_sample(name: str, sr: int = 48000) -> np.ndarray:
    """Generate numpy float32 audio buffer for drum or note names."""
    sample_name = name.lower().strip()

    if "kick" in sample_name or sample_name == "k":
        # 808 sub kick: pitch sweep 150Hz -> 45Hz over 0.25s
        duration = 0.25
        num_samples = int(sr * duration)
        t = np.linspace(0, duration, num_samples, endpoint=False, dtype=np.float32)
        freq = 45.0 + 105.0 * np.exp(-25.0 * t)
        phase = 2.0 * np.pi * np.cumsum(freq) / sr
        envelope = np.exp(-8.0 * t)
        signal = np.sin(phase) * envelope
        return cast(np.ndarray, signal.astype(np.float32))

    if "snare" in sample_name or sample_name in ("sn", "sd"):
        # Snare: noise burst + 180Hz tone pop
        duration = 0.18
        num_samples = int(sr * duration)
        t = np.linspace(0, duration, num_samples, endpoint=False, dtype=np.float32)
        tone = np.sin(2.0 * np.pi * 180.0 * t) * np.exp(-15.0 * t)
        noise = (np.random.rand(num_samples).astype(np.float32) * 2.0 - 1.0) * np.exp(-20.0 * t)
        signal = 0.4 * tone + 0.6 * noise
        return cast(np.ndarray, signal.astype(np.float32))

    if "hh" in sample_name or "hat" in sample_name or sample_name in ("ch", "oh"):
        # Hihat: high-passed noise tick
        duration = 0.08
        num_samples = int(sr * duration)
        t = np.linspace(0, duration, num_samples, endpoint=False, dtype=np.float32)
        noise = np.random.rand(num_samples).astype(np.float32) * 2.0 - 1.0
        # simple high pass diff filter
        hp_noise = np.diff(noise, prepend=0.0)
        envelope = np.exp(-40.0 * t)
        signal = hp_noise * envelope * 0.5
        return cast(np.ndarray, signal.astype(np.float32))

    if "clap" in sample_name or sample_name == "cp":
        # Clap: triple noise bursts
        duration = 0.15
        num_samples = int(sr * duration)
        t = np.linspace(0, duration, num_samples, endpoint=False, dtype=np.float32)
        noise = np.random.rand(num_samples).astype(np.float32) * 2.0 - 1.0
        envelope = (
            np.exp(-60.0 * np.clip(t, 0, 0.01))
            + 0.7 * np.exp(-60.0 * np.clip(t - 0.015, 0, None))
            + 0.5 * np.exp(-30.0 * np.clip(t - 0.03, 0, None))
        )
        signal = noise * envelope * 0.4
        return cast(np.ndarray, signal.astype(np.float32))

    # Chromatic / default synth tone
    # Parse note frequency or default to 220Hz (A3)
    freq = _note_to_freq(sample_name)
    duration = 0.3
    num_samples = int(sr * duration)
    t = np.linspace(0, duration, num_samples, endpoint=False, dtype=np.float32)
    # Warm triangle/sine blend
    tone = np.sin(2.0 * np.pi * freq * t) + 0.3 * np.sin(4.0 * np.pi * freq * t)
    envelope = np.exp(-6.0 * t)
    signal = tone * envelope * 0.4
    return cast(np.ndarray, signal.astype(np.float32))


def _note_to_freq(name: str) -> float:
    """Parse note name like C2, E2, G2, A3 into frequency in Hz."""
    notes = {"c": 0, "cs": 1, "d": 2, "ds": 3, "e": 4, "f": 5, "fs": 6, "g": 7, "gs": 8, "a": 9, "as": 10, "b": 11}
    clean = name.lower().replace("#", "s")
    note_part = "".join([c for c in clean if c.isalpha()])
    oct_part = "".join([c for c in clean if c.isdigit() or c == "-"])
    octave = int(oct_part) if oct_part else 3
    semitone = notes.get(note_part, 9)  # default A
    midi_num = (octave + 1) * 12 + semitone
    return float(440.0 * (2.0 ** ((midi_num - 69) / 12.0)))


class SynthVoice(Voice):
    """Voice that plays dynamically synthesized audio buffers."""

    def __init__(self, sample_name: str, channel: int, gain: float = 1.0, pan: float = 0.0, **kwargs: Any):
        super().__init__(channel, gain, pan)
        self.sample_name = sample_name
        self.sr = kwargs.get("sample_rate", 48000)
        self.data = generate_synthetic_sample(sample_name, sr=self.sr)
        self.position = 0
        self.length = len(self.data)
        self.is_active = True

    def generate(self, frames: int, sr: int) -> np.ndarray:
        if not self.is_active:
            return cast(np.ndarray, np.zeros(frames, dtype=np.float32))
        end_pos = self.position + frames
        if end_pos <= self.length:
            block = self.data[self.position : end_pos]
            self.position = end_pos
        else:
            remaining = self.length - self.position
            block = np.zeros(frames, dtype=np.float32)
            if remaining > 0:
                block[:remaining] = self.data[self.position :]
            self.is_active = False
        return block
