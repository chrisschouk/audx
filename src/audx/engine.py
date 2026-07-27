"""
audx — Core audio engine.

Handles:
- Audio backend (sounddevice / CoreAudio), imported lazily
- Sample playback voices (memory-mapped WAV/FLAC/MP3)
- Built-in synth voices (procedural, no samples required)
- Mix bus (16 channels)
- Real-time thread with low-latency callback

The real-time backend (``sounddevice`` → PortAudio) is imported lazily inside
:meth:`AudioEngine.start`, so importing this module — and everything that builds
on it, including the whole CLI — works on machines without the PortAudio system
library. Offline features (render, export, demo, diff) never touch the backend.
"""

from __future__ import annotations

import threading
from typing import Any, cast

import numpy as np
import sounddevice as sd
import soundfile as sf

from audx.pattern import get_pattern_engine
from audx.sampler import get_sample_library


class AudioEngine:
    """Main audio engine — runs a real-time audio callback."""

    def __init__(self, sample_rate: int = 48000, buffer_size: int = 256):
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.stream: sd.OutputStream | None = None
        self.running = False
        self.lock = threading.RLock()
        self.channels = 16
        self.mix_buffer = np.zeros((self.channels, buffer_size), dtype=np.float32)
        self.channel_levels = np.zeros(self.channels, dtype=np.float32)
        self.channel_pan = np.zeros(self.channels, dtype=np.float32)    # -1=L, +1=R
        self.channel_mute = np.zeros(self.channels, dtype=bool)
        self.channel_gain = np.ones(self.channels, dtype=np.float32)
        self.master_level = 1.0
        self.bpm = 128.0
        self.scheduler_callback = None
        self.active_voices: list[Voice] = []
        self.pattern_engine = get_pattern_engine()
        self.sample_library = get_sample_library()
        self._synth_cache: dict[str, np.ndarray] = {}

    @staticmethod
    def _backend() -> Any:
        """Import the sounddevice backend lazily with a friendly error."""
        try:
            import sounddevice as sd
        except OSError as exc:  # PortAudio missing
            raise RuntimeError(
                "Real-time audio needs the PortAudio library. Install it "
                "(macOS: `brew install portaudio`, Debian/Ubuntu: "
                "`apt install libportaudio2`) — offline render/export still work without it."
            ) from exc
        return sd

    def start(self) -> None:
        if self.stream and self.stream.active:
            return
        try:
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                blocksize=self.buffer_size,
                channels=2,
                dtype='float32',
                callback=self._audio_callback,
                finished_callback=self._stream_finished
            )
            self.stream.start()
            self.running = True
        except Exception as exc:
            self.running = False
            raise RuntimeError(f"Audio output device error: {exc}") from exc

    def stop(self) -> None:
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        self.running = False

    def _audio_callback(self, outdata: Any, frames: int, time_info: Any, status: Any) -> None:
        if status:
            print(f"[Audio] {status}")
        self.mix_buffer[:] = 0.0
        # Advance pattern scheduler
        delta_time = frames / self.sample_rate
        pattern_steps = self.pattern_engine.tick(delta_time)
        for step in pattern_steps:
            ch = max(0, min(int(step.channel), self.channels - 1))
            velocity = step.velocity
            # Resolve sample path using global sample library
            sample_path = self.sample_library.resolve(step.sample)
            sample_voice: Voice
            if sample_path and sample_path.exists():
                sample_voice = SampleVoice(str(sample_path), channel=ch, gain=velocity, pan=0.0)
                if not sample_voice.is_active:
                    from audx.audio.synth import SynthVoice

                    sample_voice = SynthVoice(step.sample, channel=ch, gain=velocity, pan=0.0, sample_rate=self.sample_rate)
            else:
                from audx.audio.synth import SynthVoice

                sample_voice = SynthVoice(step.sample, channel=ch, gain=velocity, pan=0.0, sample_rate=self.sample_rate)

            with self.lock:
                self.active_voices.append(sample_voice)

        with self.lock:
            alive: list[Voice] = []
            for voice in self.active_voices:
                if voice.is_active:
                    samples = voice.generate(frames, self.sample_rate)
                    ch = voice.channel
                    if not self.channel_mute[ch]:
                        gain = voice.gain * float(self.channel_gain[ch])
                        self.mix_buffer[ch, :] += samples * gain
                    alive.append(voice)
            self.active_voices = alive
            for ch in range(self.channels):
                self.channel_levels[ch] = (
                    float(np.sqrt(np.mean(self.mix_buffer[ch] ** 2))) if frames > 0 else 0.0
                )
        mono = np.sum(self.mix_buffer, axis=0) * self.master_level
        outdata[:, 0] = mono * 0.7
        outdata[:, 1] = mono * 0.7

    def trigger_hit(self, sample_name: str, channel: int = 0, velocity: float = 1.0) -> None:
        """Trigger an immediate sample or synth hit on a channel (e.g. from Push 2 pad)."""
        ch = max(0, min(int(channel), self.channels - 1))
        sample_path = self.sample_library.resolve(sample_name)
        sample_voice: Voice
        if sample_path and sample_path.exists():
            sample_voice = SampleVoice(str(sample_path), channel=ch, gain=velocity, pan=0.0)
            if not sample_voice.is_active:
                from audx.audio.synth import SynthVoice

                sample_voice = SynthVoice(sample_name, channel=ch, gain=velocity, pan=0.0, sample_rate=self.sample_rate)
        else:
            from audx.audio.synth import SynthVoice

            sample_voice = SynthVoice(sample_name, channel=ch, gain=velocity, pan=0.0, sample_rate=self.sample_rate)

        with self.lock:
            self.active_voices.append(sample_voice)

    def _stream_finished(self):
        self.running = False

    def play_sample(self, sample_path: str, channel: int, volume: float = 1.0, pan: float = 0.0, **kwargs: Any) -> Voice:
        with self.lock:
            voice = SampleVoice(sample_path, channel, volume, pan, **kwargs)
            self.active_voices.append(voice)
        return voice

    def set_channel_gain(self, channel: int, gain: float) -> None:
        with self.lock:
            voice = SynthVoice(buffer, channel, volume, pan)
            self.active_voices.append(voice)
        return voice

    def set_channel_pan(self, channel: int, pan: float) -> None:
        with self.lock:
            self.channel_gain[channel] = float(np.clip(gain, 0.0, 2.0))

    def set_channel_mute(self, channel: int, mute: bool) -> None:
        with self.lock:
            self.channel_mute[channel] = bool(mute)

    def set_master(self, level: float) -> None:
        with self.lock:
            self.channel_pan[channel] = float(np.clip(pan, -1, 1))

    def set_bpm(self, bpm: float) -> None:
        with self.lock:
            self.bpm = bpm
        self.pattern_engine.set_bpm(bpm)

    def get_channel_levels(self) -> np.ndarray:
        with self.lock:
            return cast(np.ndarray, self.channel_levels.copy())


class Voice:
    def __init__(self, channel: int, gain: float = 1.0, pan: float = 0.0):
        self.channel = channel
        self.gain = gain
        self.pan = pan
        self.position = 0
        self.is_active = True

    def generate(self, frames: int, sr: int) -> np.ndarray:
        raise NotImplementedError


_SAMPLE_CACHE: dict[str, tuple[np.ndarray, int]] = {}


def get_cached_sample_data(sample_path: str) -> tuple[np.ndarray, int]:
    """Retrieve pre-loaded float32 numpy audio buffer without disk I/O in realtime audio thread."""
    if sample_path in _SAMPLE_CACHE:
        return _SAMPLE_CACHE[sample_path]

    try:
        data, sr = sf.read(sample_path, dtype="float32", always_2d=False)
        data_arr = cast(np.ndarray, data)
        if data_arr.ndim > 1:
            data_arr = cast(np.ndarray, np.mean(data_arr, axis=1))
        data_arr = cast(np.ndarray, data_arr.astype(np.float32))

        max_samples = int(sr * 3.0)
        if len(data_arr) > max_samples:
            data_arr = data_arr[:max_samples]

        _SAMPLE_CACHE[sample_path] = (data_arr, int(sr))
        return data_arr, int(sr)
    except Exception:
        fallback = np.zeros(1, dtype=np.float32)
        return fallback, 44100


class SampleVoice(Voice):
    def __init__(self, sample_path: str, channel: int, gain: float, pan: float, **kwargs: Any):
        super().__init__(channel, gain, pan)
        self.sample_path = sample_path
        self.loop = kwargs.get("loop", False)
        self.start_frame = kwargs.get("start_frame", 0)
        data, sr = get_cached_sample_data(sample_path)
        self.data = data
        self.sr = sr
        self.position = self.start_frame
        self.length = len(self.data)
        self.is_active = len(self.data) > 1

    def generate(self, frames: int, sr: int) -> np.ndarray:
        if not self.is_active:
            return cast(np.ndarray, np.zeros(frames, dtype=np.float32))
        end_pos = self.position + frames
        if end_pos <= self.length:
            block = self.data[self.position:end_pos]
            self.position = end_pos
            if self.loop and end_pos >= self.length:
                self.position = 0
        else:
            remaining = self.length - self.position
            block = np.zeros(frames, dtype=np.float32)
            if remaining > 0:
                block[:remaining] = self.data[self.position:]
            self.is_active = False
        return block


_engine: AudioEngine | None = None

def get_engine() -> AudioEngine | None:
    return _engine


def init_engine(sample_rate: int | None = None, buffer_size: int | None = None) -> AudioEngine:
    global _engine
    if _engine is None:
        from audx.config import AUDX_BPM

        sr = sample_rate or 48000
        bs = buffer_size or 256
        _engine = AudioEngine(sr, bs)
        _engine.set_bpm(float(AUDX_BPM))
    return _engine
