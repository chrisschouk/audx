"""A single polyphonic voice for sample playback."""

from typing import cast

import numpy as np


class Voice:
    """One playing instance of a sample (polyphonic)."""
    def __init__(self, sample_data: np.ndarray, sample_rate: int):
        self.sample = sample_data.astype(np.float32)
        self.sr = sample_rate
        self.pos = 0.0
        self.velocity = 1.0
        self.gain = 1.0
        self.pan = 0.0  # -1 (L) to +1 (R)
        self.frequency_shift = 1.0  # pitch multiplier
        self.envelope_attack = 0.01  # seconds
        self.envelope_release = 0.05
        self._enabled = True
        self._env_value = 0.0
        self._env_state = "idle"  # idle, attack, sustain, release
        self._env_current = 0.0

    def set(self, *, velocity: float = 1.0, pan: float = 0.0, pitch_shift: float = 1.0):
        self.velocity = velocity
        self.pan = pan
        self.frequency_shift = pitch_shift
        # Trigger attack envelope
        self._env_state = "attack"
        self._env_current = 0.0

    def release(self):
        """Start envelope release."""
        if self._env_state in ("attack", "sustain"):
            self._env_state = "release"

    def process(self, frames: int) -> np.ndarray:
        """
        Generate `frames` stereo samples.
        Returns interleaved float32 array [L,R,L,R,...].
        """
        if not self._enabled:
            return cast(np.ndarray, np.zeros(frames * 2, dtype=np.float32))

        # Determine output length
        remaining = len(self.sample) - int(self.pos)
        available = min(remaining, frames)

        # Read segment (mono or stereo)
        if self.sample.ndim == 1:
            mono = self.sample[int(self.pos):int(self.pos)+available]
            # Apply pitch shift by resampling (simple linear interpolation)
            if self.frequency_shift != 1.0:
                orig_len = len(mono)
                new_len = int(orig_len / self.frequency_shift)
                indices = np.linspace(0, orig_len - 1, new_len)
                mono = cast(np.ndarray, np.interp(indices, np.arange(orig_len), mono)[:frames])
                available = len(mono)
            out = np.zeros(available * 2, dtype=np.float32)
            out[0::2] = mono * self.gain  # left
            out[1::2] = mono * self.gain  # right
        else:
            # Stereo sample
            seg = self.sample[int(self.pos):int(self.pos)+available]
            if self.frequency_shift != 1.0:
                orig_len = len(seg)
                new_len = int(orig_len / self.frequency_shift)
                indices = np.linspace(0, orig_len - 1, new_len)
                seg = cast(np.ndarray, np.array([np.interp(indices, np.arange(orig_len), seg[:, ch]) for ch in range(2)]).T)
                available = len(seg)
            out = np.zeros(available * 2, dtype=np.float32)
            out[0::2] = seg[:, 0] * self.gain
            out[1::2] = seg[:, 1] * self.gain

        # Pan (constant-power). pan -1 = hard left, 0 = centre, +1 = hard right,
        # so map [-1, 1] onto the [0, π/2] quarter-circle before taking cos/sin.
        angle = (self.pan + 1.0) * (np.pi / 4.0)
        left_gain = np.cos(angle)
        right_gain = np.sin(angle)
        out[0::2] *= left_gain
        out[1::2] *= right_gain

        # Envelope — computed per mono frame, applied to both interleaved channels.
        env = self._compute_envelope(available)
        out[0::2] *= env
        out[1::2] *= env

        # Advance position
        self.pos += available / self.frequency_shift

        # If we consumed all frames but still need to fill, zero-pad
        if available < frames:
            pad = np.zeros((frames - available) * 2, dtype=np.float32)
            out = cast(np.ndarray, np.concatenate([out, pad]))
            self._enabled = False  # voice finished

        return cast(np.ndarray, out)

    def _compute_envelope(self, frames: int) -> np.ndarray:
        sr = self.sr
        env = np.ones(frames, dtype=np.float32)

        attack_samples = int(self.envelope_attack * sr)
        release_samples = int(self.envelope_release * sr)

        if self._env_state == "attack":
            # ramp from 0 to 1; clip to the buffer when the attack is longer
            # than this block so the multiply can't broadcast-mismatch.
            ramp = np.linspace(0, 1, attack_samples, dtype=np.float32)
            n = min(attack_samples, frames)
            env[:n] *= ramp[:n]
            if frames > attack_samples:
                self._env_state = "sustain"
                self._env_current = 1.0
        elif self._env_state == "sustain":
            env[:] = 1.0
        elif self._env_state == "release":
            ramp = np.linspace(1, 0, release_samples, dtype=np.float32)
            n = min(release_samples, frames)
            env[:n] *= ramp[:n]
            if frames > release_samples:
                self._enabled = False

        return cast(np.ndarray, env)

    @property
    def is_finished(self) -> bool:
        return not self._enabled
