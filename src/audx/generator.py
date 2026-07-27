"""Genre-based multi-channel track generator."""

from __future__ import annotations

from enum import Enum

from audx.pattern import Pattern
from audx.sampler import SampleLibrary


class Genre(str, Enum):
    TECHNO = "techno"
    HOUSE = "house"
    HIPHOP = "hiphop"
    UKG = "ukg"
    AMBIENT = "ambient"


GENRE_TEMPOS: dict[Genre, float] = {
    Genre.TECHNO: 128.0,
    Genre.HOUSE: 124.0,
    Genre.HIPHOP: 90.0,
    Genre.UKG: 132.0,
    Genre.AMBIENT: 110.0,
}


def generate_track(genre: Genre = Genre.TECHNO, library: SampleLibrary | None = None) -> tuple[float, list[Pattern]]:
    """Generate multi-channel patterns for a given genre.

    Returns (bpm, list_of_patterns).
    """
    bpm = GENRE_TEMPOS.get(genre, 128.0)

    # Search library for best matching samples or use default names
    kick_name = _find_sample(library, "kick") or "kick"
    snare_name = _find_sample(library, "snare") or ("clap" if genre == Genre.HOUSE else "snare")
    hat_name = _find_sample(library, "hat") or "hh"
    bass_name = _find_sample(library, "bass") or "C2"

    patterns: list[Pattern] = []

    if genre == Genre.TECHNO:
        patterns = [
            Pattern(name="kick", dsl=f"{kick_name} 4/4 | channel 0 | gain 0dB", channel=0),
            Pattern(name="snare", dsl=f"{snare_name} 2/8 | channel 1 | vel 0.85 | gain -2dB", channel=1),
            Pattern(name="hats", dsl=f"{hat_name} 16x8 | channel 2 | vel 0.6 | swing 10%", channel=2),
            Pattern(name="sub", dsl=f"{bass_name} 4/4 | channel 3 | gain -3dB", channel=3),
        ]
    elif genre == Genre.HOUSE:
        patterns = [
            Pattern(name="kick", dsl=f"{kick_name} 4/4 | channel 0", channel=0),
            Pattern(name="clap", dsl=f"{snare_name} 2/8 | channel 1 | vel 0.9", channel=1),
            Pattern(name="hats", dsl=f"{hat_name} 16x8 | channel 2 | swing 54% | vel 0.7", channel=2),
            Pattern(name="bass", dsl=f"{bass_name} 4/4 | channel 3", channel=3),
        ]
    elif genre == Genre.HIPHOP:
        patterns = [
            Pattern(name="kick", dsl=f"{kick_name} 2/4 | channel 0", channel=0),
            Pattern(name="snare", dsl=f"{snare_name} 2/8 | channel 1 | humanize 12%", channel=1),
            Pattern(name="hats", dsl=f"{hat_name} 16x8 | channel 2 | swing 48% | chance 90%", channel=2),
            Pattern(name="bass", dsl=f"{bass_name} 4/4 | channel 3", channel=3),
        ]
    elif genre == Genre.UKG:
        patterns = [
            Pattern(name="kick", dsl=f"{kick_name} 4/4 | channel 0", channel=0),
            Pattern(name="snare", dsl=f"{snare_name} 2/8 | channel 1 | vel 0.95", channel=1),
            Pattern(name="skip_hats", dsl=f"{hat_name} 16x8 | channel 2 | swing 60%", channel=2),
            Pattern(name="sub", dsl=f"{bass_name} 4/4 | channel 3", channel=3),
        ]
    else:  # AMBIENT
        patterns = [
            Pattern(name="pulse", dsl=f"{kick_name} 1/4 | channel 0 | gain -4dB", channel=0),
            Pattern(name="echo_hat", dsl=f"{hat_name} 4x8 | channel 1 | chance 70%", channel=1),
            Pattern(name="pad", dsl=f"{bass_name} 1/4 | channel 2 | gain -6dB", channel=2),
        ]

    for p in patterns:
        p.parse_dsl()

    return bpm, patterns


def _find_sample(library: SampleLibrary | None, tag: str) -> str | None:
    if library is None:
        return None
    matches = library.search(tag, limit=1)
    if matches:
        return tag
    return None
