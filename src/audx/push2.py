"""Push 2 MIDI mapping, pad lighting, and device detection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import mido


@dataclass(frozen=True)
class Push2Control:
    name: str
    midi_type: str
    number: int
    description: str


DEFAULT_PUSH2_MAP = [
    Push2Control("play", "note", 85, "Transport play"),
    Push2Control("stop", "note", 86, "Transport stop"),
    Push2Control("record", "note", 87, "Record/arm placeholder"),
    Push2Control("tap_tempo", "note", 3, "Tap tempo"),
    Push2Control("encoder_1", "cc", 14, "Channel 1 gain"),
    Push2Control("encoder_2", "cc", 15, "Channel 2 gain"),
    Push2Control("encoder_3", "cc", 16, "Channel 3 gain"),
    Push2Control("encoder_4", "cc", 17, "Channel 4 gain"),
]


def list_push2_map() -> list[Push2Control]:
    return DEFAULT_PUSH2_MAP.copy()


def find_push2_output() -> str | None:
    """Find Push 2 MIDI output port name."""
    try:
        for name in mido.get_output_names():
            if "push" in name.lower():
                return str(name)
    except Exception:
        pass
    return None


def find_push2_input() -> str | None:
    """Find Push 2 MIDI input port name."""
    try:
        for name in mido.get_input_names():
            if "push" in name.lower():
                return str(name)
    except Exception:
        pass
    return None


def light_push2_pads(port_name: str | None = None) -> bool:
    """Send MIDI note colors to light up the 64-pad grid on Push 2 hardware."""
    target_port = port_name or find_push2_output()
    if not target_port:
        return False

    try:
        with mido.open_output(target_port) as port:
            # Push 2 pads 36..99 (8x8 grid)
            for note in range(36, 100):
                # Cycle pad colors (12=green, 45=blue, 127=red, 21=cyan)
                color = 12 if note % 4 == 0 else (45 if note % 4 == 1 else (127 if note % 4 == 2 else 21))
                port.send(mido.Message("note_on", note=note, velocity=color, channel=0))
        return True
    except Exception:
        return False
