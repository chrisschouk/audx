"""Tests for the standalone audio engine package (src/audx/audio/).

This package isn't yet wired into the CLI/TUI, but its DSP has to be correct for
when it is: constant-power panning, an envelope that survives short buffers, and
solo handling in the mixer.
"""

import numpy as np

from audx.audio.mixer import Mixer
from audx.audio.voice import Voice


def _voice(frames: int = 64) -> Voice:
    v = Voice(np.ones(frames, dtype=np.float32), 44100)
    v.gain = 1.0
    return v


def test_pan_centre_is_equal_across_channels():
    v = _voice()
    v.pan = 0.0
    out = v.process(64)
    assert np.allclose(out[0::2], out[1::2])
    assert float(np.max(np.abs(out))) > 0.0  # centre is audible, not silent


def test_pan_hard_left_and_right():
    left = _voice()
    left.pan = -1.0
    lo = left.process(64)
    assert float(np.max(np.abs(lo[0::2]))) > 0.9
    assert np.allclose(lo[1::2], 0.0, atol=1e-6)

    right = _voice()
    right.pan = 1.0
    ro = right.process(64)
    assert np.allclose(ro[0::2], 0.0, atol=1e-6)
    assert float(np.max(np.abs(ro[1::2]))) > 0.9


def test_envelope_longer_than_buffer_does_not_crash():
    v = Voice(np.ones(8000, dtype=np.float32), 44100)
    v.set(velocity=1.0)  # triggers the attack envelope
    v.envelope_attack = 0.1  # 4410 samples, far larger than the 256-frame block
    out = v.process(256)  # would raise a broadcast ValueError before the fix
    assert len(out) == 256 * 2


def test_mixer_solo_excludes_non_soloed_channels():
    mix = Mixer(channels=2, sample_rate=44100)
    mix.channels[1].add_voice(_voice())  # sound lives only on channel 1
    mix.channels[0].solo = True  # solo the (silent) channel 0
    out = mix.process(64)
    assert float(np.max(np.abs(out))) < 1e-6  # channel 1 is excluded by solo

    mix2 = Mixer(channels=2, sample_rate=44100)
    mix2.channels[1].add_voice(_voice())
    mix2.channels[1].solo = True  # solo the channel that has sound
    out2 = mix2.process(64)
    assert float(np.max(np.abs(out2))) > 0.0
