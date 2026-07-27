"""Ableton Live Set (.als) export module."""

from __future__ import annotations

import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

from audx.project import Project


def project_to_als(project: Project, output_path: Path) -> Path:
    """Export an audx Project to a native GZipped Ableton Live Set (.als) file."""
    output_path = Path(output_path)
    if output_path.suffix.lower() != ".als":
        output_path = output_path.with_suffix(".als")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    root = ET.Element(
        "Ableton",
        {
            "MajorVersion": "11",
            "MinorVersion": "1.0",
            "SchemaChangeCount": "3",
            "Creator": "audx 0.2.0",
            "Revision": "1",
        },
    )

    live_set = ET.SubElement(root, "LiveSet")

    # Tempo / Master Transport
    master_track = ET.SubElement(live_set, "MasterTrack")
    master_device_chain = ET.SubElement(master_track, "MasterChain")
    tempo_elem = ET.SubElement(master_device_chain, "Tempo")
    ET.SubElement(tempo_elem, "Manual", {"Value": str(project.bpm)})

    tracks_elem = ET.SubElement(live_set, "Tracks")

    # Group patterns by channel or name
    for i, pattern_data in enumerate(project.patterns):
        name = pattern_data.get("name", f"Track_{i+1}")
        channel = pattern_data.get("channel", i)
        dsl = pattern_data.get("dsl", "")

        midi_track = ET.SubElement(tracks_elem, "MidiTrack", {"Id": str(i + 1)})
        ET.SubElement(midi_track, "Name", {"Value": name})
        ET.SubElement(midi_track, "Channel", {"Value": str(channel)})

        device_chain = ET.SubElement(midi_track, "DeviceChain")
        main_sequencer = ET.SubElement(device_chain, "MainSequencer")
        clip_slot_list = ET.SubElement(main_sequencer, "ClipSlotList")
        clip_slot = ET.SubElement(clip_slot_list, "ClipSlot", {"Id": "0"})
        clip_slot_val = ET.SubElement(clip_slot, "Value")

        midi_clip = ET.SubElement(clip_slot_val, "MidiClip", {"Time": "0", "Name": dsl or name})
        ET.SubElement(midi_clip, "Loop", {"LoopStart": "0", "LoopEnd": "4", "StartRelative": "0", "IsEnabled": "true"})

        # Key tracks / notes
        notes_elem = ET.SubElement(midi_clip, "Notes")
        key_tracks = ET.SubElement(notes_elem, "KeyTracks")
        key_track = ET.SubElement(key_tracks, "KeyTrack", {"Id": "0"})
        ET.SubElement(key_track, "MidiKey", {"Value": str(36 + i)})  # C1, D1, E1 drum notes

    # Add Mixer settings if available
    mixer_elem = ET.SubElement(live_set, "Mixer")
    for i, ch_data in enumerate(project.mixer):
        ch_num = ch_data.get("channel", i)
        ch_gain = ch_data.get("gain", 1.0)
        ch_mute = "true" if ch_data.get("mute", False) else "false"
        ch_elem = ET.SubElement(mixer_elem, "Channel", {"Index": str(ch_num)})
        ET.SubElement(ch_elem, "Volume", {"Value": str(ch_gain)})
        ET.SubElement(ch_elem, "Mute", {"Value": ch_mute})

    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    gzipped_bytes = gzip.compress(xml_bytes)

    output_path.write_bytes(gzipped_bytes)
    return output_path
