"""Push 2 MIDI mapping, pad lighting, USB display driver, direct USB MIDI reader, and device detection.

Full implementation of Ableton Push 2 hardware protocol:
- Direct USB MIDI: Reads raw 4-byte USB MIDI packets directly from Bulk Endpoint 0x82 (bypassing OS MIDI stack).
- Display Driver: 960x160 BGR565 XOR 0xE73C frame buffer over USB Bulk Endpoint 0x01 (Vendor ID 0x2982, Product ID 0x1967).
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
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
    Push2Control("encoder_1", "cc", 71, "Channel 1 gain"),
    Push2Control("encoder_2", "cc", 72, "Channel 2 gain"),
    Push2Control("encoder_3", "cc", 73, "Channel 3 gain"),
    Push2Control("encoder_4", "cc", 74, "Channel 4 gain"),
    Push2Control("encoder_5", "cc", 75, "Channel 1 pan"),
    Push2Control("encoder_6", "cc", 76, "Channel 2 pan"),
    Push2Control("encoder_7", "cc", 77, "Channel 3 pan"),
    Push2Control("encoder_8", "cc", 78, "Channel 4 pan"),
    Push2Control("tempo_encoder", "cc", 14, "BPM tempo adjust"),
    Push2Control("swing_encoder", "cc", 15, "Swing percent adjust"),
    Push2Control("master_encoder", "cc", 79, "Master volume level"),
    Push2Control("track_mute_1", "note", 20, "Channel 1 Mute toggle"),
    Push2Control("track_mute_2", "note", 21, "Channel 2 Mute toggle"),
    Push2Control("track_mute_3", "note", 22, "Channel 3 Mute toggle"),
    Push2Control("track_mute_4", "note", 23, "Channel 4 Mute toggle"),
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


def render_push2_display_frame(
    bpm: float = 128.0,
    genre: str = "TECHNO",
    channel_levels: list[float] | None = None,
    channel_gains: list[float] | None = None,
) -> bytes:
    """Generate 327,696-byte USB bulk payload for Ableton Push 2 960x160 LCD screen."""
    header = b"\xff\xcc\xaa\x88\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    words = np.zeros((160, 1024), dtype=np.uint16)

    # Background (BGR565)
    bg_color = (15 & 0x1F) | ((8 & 0x3F) << 5) | ((5 & 0x1F) << 11)
    words[:, :960] = bg_color

    # Top Banner Header (px 0..32)
    header_color = (31 & 0x1F) | ((40 & 0x3F) << 5) | ((5 & 0x1F) << 11)
    words[0:32, :960] = header_color

    # Title Box
    words[4:28, 20:180] = 0xFFFF

    # Genre Badge
    yellow_pixel = (0 & 0x1F) | ((63 & 0x3F) << 5) | ((31 & 0x1F) << 11)
    words[6:26, 750:920] = yellow_pixel

    levels = channel_levels or [0.7, 0.5, 0.4, 0.8]
    gains = channel_gains or [1.0, 1.0, 1.0, 1.0]

    ch_colors = [
        (0 & 0x1F) | ((63 & 0x3F) << 5) | ((0 & 0x1F) << 11),
        (31 & 0x1F) | ((63 & 0x3F) << 5) | ((0 & 0x1F) << 11),
        (31 & 0x1F) | ((0 & 0x3F) << 5) | ((31 & 0x1F) << 11),
        (0 & 0x1F) | ((63 & 0x3F) << 5) | ((31 & 0x1F) << 11),
    ]

    for i in range(min(4, len(levels))):
        col_start = 30 + i * 230
        col_end = col_start + 200
        val = max(0.0, min(1.0, levels[i]))

        words[40:70, col_start:col_end] = (25 & 0x1F) | ((25 & 0x3F) << 5) | ((25 & 0x1F) << 11)
        words[44:66, col_start + 10 : col_start + 40] = ch_colors[i]

        meter_bg = (10 & 0x1F) | ((5 & 0x3F) << 5) | ((3 & 0x1F) << 11)
        words[80:150, col_start + 10 : col_start + 60] = meter_bg

        meter_h = int(70 * val)
        if meter_h > 0:
            words[150 - meter_h : 150, col_start + 10 : col_start + 60] = ch_colors[i]

        gain_val = max(0.0, min(2.0, gains[i])) / 2.0
        gain_h = int(70 * gain_val)
        words[80:150, col_start + 80 : col_start + 180] = (20 & 0x1F) | ((20 & 0x3F) << 5) | ((20 & 0x1F) << 11)
        if gain_h > 0:
            words[150 - gain_h : 150, col_start + 80 : col_start + 180] = ch_colors[i]

    # Hardware XOR Scrambling Mask: 0xE73C
    words ^= 0xE73C
    return bytes(header + words.tobytes())


class Push2DisplayDriver:
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
                    usb.util.claim_interface(self.device, 0)
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
            self.device.write(self.ENDPOINT_OUT, frame_bytes, timeout=500)
            return True
        except Exception:
            self._connected = False
            return False


class Push2UsbMidi:
    """Direct USB Bulk Endpoint 0x82 MIDI Listener for Push 2 on macOS."""

    VENDOR_ID = 0x2982
    PRODUCT_ID = 0x1967
    ENDPOINT_IN = 0x82

    def __init__(self, callback: Callable[[str, int, int, int], None]):
        self.callback = callback
        self.running = False
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        self.running = True
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False

    def _worker(self) -> None:
        try:
            import usb.core
            import usb.util

            dev = usb.core.find(idVendor=self.VENDOR_ID, idProduct=self.PRODUCT_ID)
            if dev is None:
                return
            try:
                if dev.is_kernel_driver_active(2):
                    dev.detach_kernel_driver(2)
            except Exception:
                pass
            try:
                usb.util.claim_interface(dev, 2)
            except Exception:
                pass

            while self.running:
                try:
                    data = dev.read(self.ENDPOINT_IN, 64, timeout=200)
                    if data and len(data) >= 4:
                        for i in range(0, len(data), 4):
                            packet = data[i : i + 4]
                            if len(packet) == 4:
                                _header, status, d1, d2 = packet
                                msg_type = status & 0xF0
                                ch = status & 0x0F
                                if msg_type == 0x90 and d2 > 0:
                                    self.callback("note_on", d1, d2, ch)
                                elif msg_type == 0x80 or (msg_type == 0x90 and d2 == 0):
                                    self.callback("note_off", d1, d2, ch)
                                elif msg_type == 0xB0:
                                    self.callback("control_change", d1, d2, ch)
                except Exception:
                    pass
                time.sleep(0.005)
        except Exception:
            pass
