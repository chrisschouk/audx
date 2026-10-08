#!/usr/bin/env python3
"""Build the promo beat and a frame-accurate data track for the Remotion video.

The beat is a UK garage 2-step loop at 132 BPM, sequenced by audx itself:

1. Synthesise one-shots (kick, clap, snare, rim, hats, shaker, sub notes and
   electric-piano chords) into a scratch sample folder.
2. Sequence each part with audx's Song/render_song engine (swing, velocity, pan).
3. Mix the stems: kick sidechain on bass and keys, reverb send, bus glue.
4. Set loudness with ffmpeg loudnorm and trim to the 20 second video.
5. Write a JSON sidecar so the video's grid, playhead and scope follow the audio.

Run:  uv run python marketing/build-beat.py      (needs ffmpeg on PATH)
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

from audx.arrangement import Song, render_song
from audx.sampler import SampleLibrary

SR = 44100
FPS = 30
BPM = 132.0
SWING = 0.22
VIDEO_SECONDS = 20.0
STEPS_PER_BAR = 16

ROOT = Path(__file__).resolve().parent / "remotion"
WAV_OUT = ROOT / "public" / "audx-beat.wav"
JSON_OUT = ROOT / "src" / "beat-data.json"

rng = np.random.default_rng(7)


def t(sec):
    return np.arange(int(sec * SR)) / SR


def sos(kind, f, order=2):
    return signal.butter(order, f, btype=kind, fs=SR, output="sos")


def bp(x, lo, hi, order=2):
    return signal.sosfilt(signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x)


def filt(x, *specs):
    for kind, f in specs:
        x = signal.sosfilt(sos(kind, f), x, axis=0)
    return x


# ── one-shots ────────────────────────────────────────────────────────────────


def synth_samples(folder: Path) -> None:
    def save(name, x):
        x = x / (np.max(np.abs(x)) + 1e-12) * 0.9
        n = int(0.004 * SR)
        x[-n:] *= np.linspace(1, 0, n)
        sf.write(folder / f"{name}.wav", x.astype(np.float32), SR)

    tt = t(0.42)
    f = 50 + (175 - 50) * np.exp(-tt / 0.028)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.22)
    click = bp(rng.standard_normal(len(tt)), 1800, 7000) * np.exp(-tt / 0.004) * 0.35
    save("jx_kick", np.tanh(1.6 * (body + click)))

    tt = t(0.45)
    noise = bp(rng.standard_normal(len(tt)), 900, 5200)
    env = np.zeros(len(tt))
    for off in (0.0, 0.011, 0.021):
        s = int(off * SR)
        env[s:] += np.exp(-(tt[: len(tt) - s]) / 0.0065)
    s = int(0.03 * SR)
    env[s:] += 0.85 * np.exp(-(tt[: len(tt) - s]) / 0.16)
    save("jx_clap", noise * env)

    tt = t(0.3)
    tone = (np.sin(2 * np.pi * 190 * tt) + 0.4 * np.sin(2 * np.pi * 330 * tt)) * np.exp(-tt / 0.05)
    nz = bp(rng.standard_normal(len(tt)), 1800, 9000) * np.exp(-tt / 0.12)
    save("jx_snare", 0.6 * tone + nz)

    tt = t(0.12)
    rim = (np.sin(2 * np.pi * 1650 * tt) + 0.7 * np.sin(2 * np.pi * 520 * tt)) * np.exp(-tt / 0.018)
    save("jx_rim", rim + bp(rng.standard_normal(len(tt)), 2000, 6000) * np.exp(-tt / 0.004) * 0.5)

    def metal(sec, decay):
        tt = t(sec)
        freqs = (205.3, 304.4, 369.6, 522.7, 540.0, 800.0)  # 808-style square bank
        x = sum(np.sign(np.sin(2 * np.pi * fr * 2.1 * tt + i)) for i, fr in enumerate(freqs))
        x = bp(x, 7000, 13500, order=3) + 0.35 * bp(rng.standard_normal(len(tt)), 8000, 14000)
        env = np.exp(-tt / decay)
        a = int(0.0008 * SR)
        env[:a] *= np.linspace(0, 1, a)
        return x * env

    save("jx_hat", metal(0.09, 0.022))
    save("jx_ohat", metal(0.45, 0.13))
    tt = t(0.12)
    save(
        "jx_shaker",
        bp(rng.standard_normal(len(tt)), 4500, 11000)
        * (1 - np.exp(-tt / 0.006))
        * np.exp(-tt / 0.045),
    )

    notes = {"F1": 43.65, "Db2": 69.30, "Bb1": 58.27, "C2": 65.41}
    for name, fr in notes.items():
        tt = t(0.6)
        x = np.tanh(1.8 * (np.sin(2 * np.pi * fr * tt) + 0.22 * np.sin(4 * np.pi * fr * tt)))
        env = (1 - np.exp(-tt / 0.004)) * np.exp(-tt / 0.45)
        save(f"jx_bass_{name}", filt(x * env, ("low", 900)))

    def midi(n):
        return 440.0 * 2 ** ((n - 69) / 12)

    chords = {  # rootless voicings, the bass plays the root
        "Fm9": [56, 60, 63, 67],
        "Dbmaj9": [53, 56, 60, 63],
        "Bbm9": [61, 65, 68, 72],
        "Cm7": [58, 63, 67, 70],
    }
    for name, ns in chords.items():
        tt = t(0.9)
        x = np.zeros(len(tt))
        for i, n in enumerate(ns):  # two-operator FM electric piano
            fr = midi(n) * (1 + 0.0015 * (i - 1.5))
            index = 1.6 * np.exp(-tt / 0.18) + 0.25
            x += np.sin(2 * np.pi * fr * tt + index * np.sin(2 * np.pi * fr * tt))
        env = (1 - np.exp(-tt / 0.003)) * np.exp(-tt / 0.32)
        save(f"jx_ep_{name}", filt(x * env, ("low", 5200)))


# ── sequencing (audx does this part) ─────────────────────────────────────────


def g(s: str) -> str:
    """16-character x/- grid to an audx bracket grid."""
    return "[" + "".join("1" if c == "x" else "0" for c in s) + "]"


SW = f"swing {round(SWING * 100)}%"
DRUMS = {
    "kick": [f"jx_kick {g('x---------x-----')} | {SW}"],
    "clap": [
        f"jx_clap {g('----x-------x---')} | vel 0.9 | {SW}",
        f"jx_snare {g('----x-------x---')} | vel 0.45 | {SW}",
    ],
    "ghost": [f"jx_rim {g('---x----------xx')} | vel 0.32 | pan 0.35 | {SW}"],
    "hats": [
        f"jx_hat {g('x---x---x---x---')} | vel 0.42 | {SW}",
        f"jx_hat {g('-x-x-x-x-x-x-x-x')} | vel 0.2 | pan -0.2 | {SW}",
        f"jx_ohat {g('--x---x---x---x-')} | vel 0.3 | pan 0.15 | {SW}",
        f"jx_shaker {g('xxxxxxxxxxxxxxxx')} | vel 0.14 | pan 0.4 | {SW}",
    ],
}
CHORD_GRID = "x-----x---x-----"
BASS_GRID = "x---------x--x--"
# (chord, bass root, bars, intro). The intro has keys and hats only.
SEQ = [
    ("Fm9", "F1", 2, True),
    ("Fm9", "F1", 2, False),
    ("Dbmaj9", "Db2", 2, False),
    ("Bbm9", "Bb1", 1, False),
    ("Cm7", "C2", 1, False),
    ("Fm9", "F1", 2, False),
    ("Dbmaj9", "Db2", 1, False),
    ("Cm7", "C2", 1, False),
]
INTRO_BARS = sum(b for *_, b, intro in SEQ if intro)


def render_stem(part: str, lib: SampleLibrary, folder: Path) -> np.ndarray:
    sections, sequence = {}, []
    for i, (ch, root, bars, intro) in enumerate(SEQ):
        pats: list[str] = []
        if part == "chords":
            pats = [f"jx_ep_{ch} {g(CHORD_GRID)} | vel 0.75 | {SW}"]
        elif part == "bass" and not intro:
            pats = [f"jx_bass_{root} {g(BASS_GRID)} | {SW}"]
        elif part in ("kick", "clap", "ghost") and not intro:
            pats = DRUMS[part]
        elif part == "hats":
            pats = DRUMS["hats"]
        sections[f"s{i}"] = {"patterns": pats, "bars": bars}
        sequence.append(f"s{i}")
    song = Song.from_spec(bpm=BPM, sections=sections, sequence=sequence)
    path = folder / f"{part}.wav"
    render_song(song, lib, path, sample_rate=SR)
    return sf.read(path, always_2d=True)[0]


# ── mix ──────────────────────────────────────────────────────────────────────

GAIN_DB = {"kick": 0, "bass": -4, "clap": 3, "ghost": 1, "hats": -2, "chords": 8, "verb": -3}


def mix(stems: dict[str, np.ndarray]) -> np.ndarray:
    n = max(len(v) for v in stems.values())
    s = {k: np.pad(v, ((0, n - len(v)), (0, 0))) for k, v in stems.items()}

    def db(k):
        return 10 ** (GAIN_DB[k] / 20)

    mix_rng = np.random.default_rng(3)

    kick = filt(s["kick"], ("high", 30))
    kick = kick + filt(kick, ("high", 85), ("low", 150)) * 0.8
    kenv = signal.sosfilt(sos("low", 14, 1), np.abs(kick[:, 0]))
    kenv = np.clip(kenv / kenv.max() * 1.6, 0, 1)

    def duck(depth):
        return (1 - depth * kenv)[:, None]

    b0 = filt(s["bass"], ("low", 240), ("high", 34))
    bass = (b0 + filt(np.tanh(b0 * 3.0), ("high", 90), ("low", 320)) * 0.6) * duck(0.6)
    chords = filt(s["chords"], ("high", 200))
    chords = (chords + (10 ** (2 / 20) - 1) * filt(chords, ("high", 2500))) * duck(0.25)
    d = int(0.012 * SR)
    chords[:, 1] = np.concatenate([np.zeros(d), chords[:-d, 1]])  # Haas width
    clap = filt(s["clap"], ("high", 180), ("low", 9000))
    ghost = filt(s["ghost"], ("high", 300))
    hats = filt(s["hats"], ("high", 4500), ("low", 10500))

    ir_t = np.arange(int(1.8 * SR)) / SR
    ir = np.stack(
        [
            filt(mix_rng.standard_normal(len(ir_t)), ("high", 350), ("low", 7500))
            * np.exp(-ir_t / 0.42)
            for _ in range(2)
        ],
        1,
    )
    ir /= np.sqrt((ir**2).sum(0))
    send = chords * 0.4 + clap * 0.25 + ghost * 0.25
    verb = np.stack([signal.fftconvolve(send[:, c], ir[:, c])[:n] for c in range(2)], 1)

    out = (
        kick * db("kick")
        + bass * db("bass")
        + clap * db("clap")
        + ghost * db("ghost")
        + hats * db("hats")
        + chords * db("chords")
        + verb * db("verb")
    )

    # bus glue: slow RMS compressor, 2:1 above the 70th percentile
    rms = np.sqrt(signal.sosfilt(sos("low", 6, 1), (out**2).mean(1)).clip(1e-12))
    thr = np.percentile(rms, 70)
    out = out * np.where(rms > thr, (thr / rms) ** 0.5, 1.0)[:, None]
    out = np.tanh(out / np.abs(out).max() * 1.15)
    return out / np.abs(out).max() * 0.89


# ── video sidecar ────────────────────────────────────────────────────────────

ROWS = [  # (label, grid, plays in the intro)
    ("kick", "x---------x-----", False),
    ("clap", "----x-------x---", False),
    ("hats", "xx-xxx-xxx-xxx-x", True),
    ("open hat", "--x---x---x---x-", True),
    ("rim", "---x----------xx", False),
    ("bass", BASS_GRID, False),
    ("keys", CHORD_GRID, True),
]


def write_sidecar() -> None:
    spb = 60.0 / BPM
    bars = sum(b for *_, b, _ in SEQ)
    tracks = []
    for name, grid, in_intro in ROWS:
        steps = [1 if c == "x" else 0 for c in grid]
        hits = []
        for bar in range(bars):
            if bar < INTRO_BARS and not in_intro:
                continue
            for st, on in enumerate(steps):
                if on:
                    sec = (bar * 4 + st / 4 + (SWING / 4 if st % 2 else 0)) * spb
                    if sec < VIDEO_SECONDS:
                        hits.append(round(sec * FPS))
        tracks.append({"name": name, "color": "#ececea", "steps": steps, "hits": hits})

    audio, _ = sf.read(WAV_OUT, always_2d=True)
    mono = audio.mean(1)
    total_frames = int(np.ceil(len(mono) / SR * FPS))
    spf = SR / FPS
    env = np.array(
        [
            np.sqrt(np.mean(c**2)) if (c := mono[int(f * spf) : int((f + 1) * spf)]).size else 0.0
            for f in range(total_frames)
        ]
    )
    env /= env.max()
    n_peaks = 1400
    w = len(mono) // n_peaks
    peaks = [round(float(np.abs(mono[i * w : (i + 1) * w]).max()), 4) for i in range(n_peaks)]

    data = {
        "bpm": BPM,
        "fps": FPS,
        "bars": bars,
        "stepsPerBar": STEPS_PER_BAR,
        "framesPerBar": 4 * spb * FPS,
        "framesPerStep": spb / 4 * FPS,
        "audioDurationFrames": total_frames,
        "tracks": tracks,
        "envelope": [round(float(x), 4) for x in env],
        "waveform": peaks,
    }
    JSON_OUT.write_text(json.dumps(data))


def main() -> None:
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is required for the loudness pass")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        samples, stems = tmp / "samples", tmp / "stems"
        samples.mkdir()
        stems.mkdir()
        synth_samples(samples)
        lib = SampleLibrary(samples)
        lib.build_index(recursive=False)
        parts = {
            p: render_stem(p, lib, stems)
            for p in ("kick", "clap", "ghost", "hats", "bass", "chords")
        }
        premaster = tmp / "premaster.wav"
        sf.write(premaster, mix(parts).astype(np.float32), SR)
        WAV_OUT.parent.mkdir(parents=True, exist_ok=True)
        fade_at = VIDEO_SECONDS - 1.6
        subprocess.run(
            [
                "ffmpeg",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(premaster),
                "-af",
                f"loudnorm=I=-11:TP=-1.0:LRA=7,atrim=0:{VIDEO_SECONDS},afade=t=out:st={fade_at}:d=1.6",
                "-ar",
                str(SR),
                str(WAV_OUT),
            ],
            check=True,
        )
    write_sidecar()
    print(f"wrote {WAV_OUT} and {JSON_OUT}")


if __name__ == "__main__":
    main()
