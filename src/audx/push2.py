"""Push 2 MIDI mapping, pad lighting, USB display driver, and device detection.

Includes full implementation of the Ableton Push 2 display protocol:
- Resolution: 960x160 pixels
- Stride: 2048 bytes / 1024 words per line (960 active pixels + 64 padding words)
- Pixel format: BGR565 XORed with Ableton's hardware scrambling mask 0xE73C
- USB Transfer: 16-byte header + 327,680 byte payload to Bulk Endpoint 0x01
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import mido
import numpy as np


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
            for note in range(36, 100):
                color = 12 if note % 4 == 0 else (45 if note % 4 == 1 else (127 if note % 4 == 2 else 21))
                port.send(mido.Message("note_on", note=note, velocity=color, channel=0))
        return True
    except Exception:
        return False


def render_push2_display_frame(bpm: float = 128.0, genre: str = "TECHNO", channel_levels: list[float] | None = None) -> bytes:
    """Generate 327,696-byte USB bulk payload for Ableton Push 2 960x160 LCD screen."""
    # 16-byte Ableton Push 2 display header
    header = b"\xff\xcc\xaa\x88\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"

    # 160 lines x 1024 uint16 words (960 active pixels + 64 padding words)
    words = np.zeros((160, 1024), dtype=np.uint16)

    # Dark cyan/navy background (BGR565: Blue=20, Green=10, Red=5)
    bg_color = (20 & 0x1F) | ((10 & 0x3F) << 5) | ((5 & 0x1F) << 11)
    words[:, :960] = bg_color

    # Top Header Bar (0..32 px) - Magenta/Teal accent
    header_color = (15 & 0x1F) | ((45 & 0x3F) << 5) | ((25 & 0x1F) << 11)
    words[0:32, :960] = header_color

    # Draw 4 Channel Strips (columns 0..4)
    levels = channel_levels or [0.8, 0.6, 0.4, 0.9]
    for i in range(min(4, len(levels))):
        col_start = 40 + i * 220
        col_end = col_start + 180
        val = levels[i]

        # Channel header box (px 40..65)
        ch_box_color = (28 & 0x1F) | ((20 & 0x3F) << 5) | ((10 & 0x1F) << 11)
        words[40:65, col_start:col_end] = ch_box_color

        # Level meter bar (px 75..145)
        meter_height = int(70 * val)
        if meter_height > 0:
            meter_color = (5 & 0x1F) | ((60 & 0x3F) << 5) | ((10 & 0x1F) << 11)
            words[145 - meter_height : 145, col_start : col_start + 40] = meter_color

    # CRITICAL: Ableton Push 2 Hardware Display Scrambling XOR Mask: 0xE73C
    words ^= 0xE73C

    return bytes(header + words.tobytes())


class Push2DisplayDriver:
    """USB Bulk Display Driver for Ableton Push 2 onboard 960x160 color LCD screen.

    Ableton Push 2 USB Hardware Specs:
    - Vendor ID: 0x2982 (Ableton AG)
    - Product ID: 0x1967 (Push 2)
    - Interface 0: Push 2 Display (Bulk Endpoint 0x01 OUT)
    - Resolution: 960x160 pixels (2048-byte stride per line)
    - Protocol: 16-byte header + 327,680 byte payload (BGR565 XOR 0xE73C)
    """

    VENDOR_ID = 0x2982
    PRODUCT_ID = 0x1967
    ENDPOINT_OUT = 0x01

    def __init__(self) -> None:
        self.device: Any | None = None
        self._connected = False
        self._init_usb()

    def _init_usb(self) -> bool:
        try:
            import usb.core
            import usb.util

            self.device = usb.core.find(idVendor=self.VENDOR_ID, idProduct=self.PRODUCT_ID)
            if self.device is not None:
                try:
                    if self.device.is_kernel_driver_active(0):
                        self.device.detach_kernel_driver(0)
                except Exception:
                    pass
                try:
                    self.device.set_configuration()
                except Exception:
                    pass
                self._connected = True
                return True
        except Exception:
            pass
        self._connected = False
        return False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def send_frame(self, frame_bytes: bytes) -> bool:
        if self.device is None:
            if not self._init_usb():
                return False
        if self.device is None:
            return False
        try:
            self.device.write(self.ENDPOINT_OUT, frame_bytes, timeout=1000)
            return True
        except Exception:
            self._connected = False
            return False
