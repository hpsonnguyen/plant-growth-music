from __future__ import annotations

import struct
from pathlib import Path

import pandas as pd

from .config import output_path


def _vlq(value: int) -> bytes:
    bytes_out = [value & 0x7F]
    value >>= 7
    while value:
        bytes_out.insert(0, (value & 0x7F) | 0x80)
        value >>= 7
    return bytes(bytes_out)


def _track_chunk(data: bytes) -> bytes:
    return b"MTrk" + struct.pack(">I", len(data)) + data


def _meta(delta: int, meta_type: int, payload: bytes) -> bytes:
    return _vlq(delta) + bytes([0xFF, meta_type]) + _vlq(len(payload)) + payload


def _text_meta(delta: int, meta_type: int, text: str) -> bytes:
    return _meta(delta, meta_type, text.encode("utf-8"))


def _channel(delta: int, status: int, data1: int, data2: int | None = None) -> bytes:
    payload = bytes([status, data1]) if data2 is None else bytes([status, data1, data2])
    return _vlq(delta) + payload


def _tempo_track(config: dict) -> bytes:
    timeline = config["timeline"]
    tempo = int(60_000_000 / int(timeline["bpm"]))
    data = b""
    data += _text_meta(0, 0x03, "Plant Music Tempo")
    data += _meta(0, 0x51, tempo.to_bytes(3, "big"))
    data += _meta(0, 0x58, bytes([int(timeline["meter_numerator"]), 2, 24, 8]))
    data += _meta(0, 0x2F, b"")
    return _track_chunk(data)


def _stem_track(config: dict, batch: str, events: pd.DataFrame) -> bytes:
    stem = _track_config(config, batch, events)
    ticks_per_beat = int(config["timeline"]["ticks_per_beat"])
    data = b""
    data += _text_meta(0, 0x03, stem["track_name"])
    if events.empty:
        data += _channel(0, 0xC0 + int(stem["channel"]), int(stem["program"]))
    else:
        for channel, program in sorted(events.groupby("channel")["program"].first().items()):
            data += _channel(0, 0xC0 + int(channel), int(program))
    midi_events: list[tuple[int, int, bytes]] = []
    for _, event in events.iterrows():
        start = int(round(float(event["beat_start"]) * ticks_per_beat))
        end = int(round((float(event["beat_start"]) + float(event["beat_duration"])) * ticks_per_beat))
        pitch = int(event["pitch_midi"])
        velocity = int(event["velocity"])
        channel = int(event["channel"])
        midi_events.append((start, 1, bytes([0x90 + channel, pitch, velocity])))
        midi_events.append((max(start + 1, end), 0, bytes([0x80 + channel, pitch, 0])))
    midi_events.sort(key=lambda item: (item[0], item[1]))
    last_tick = 0
    for tick, _, payload in midi_events:
        data += _vlq(max(0, tick - last_tick)) + payload
        last_tick = tick
    data += _meta(0, 0x2F, b"")
    return _track_chunk(data)


def _track_config(config: dict, batch: str, events: pd.DataFrame) -> dict:
    if batch in config["stems"]:
        return config["stems"][batch]
    if batch == "ACCOMP" and "accompaniment" in config:
        return config["accompaniment"]
    if not events.empty:
        row = events.iloc[0]
        return {"track_name": str(row["track_name"]), "channel": int(row["channel"]), "program": int(row["program"])}
    raise ValueError(f"No track configuration for batch '{batch}'")


def _write_midi(path: Path, config: dict, tracks: list[bytes]) -> None:
    ticks = int(config["timeline"]["ticks_per_beat"])
    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks), ticks)
    path.write_bytes(header + b"".join(tracks))


def export_midi(config: dict, events: pd.DataFrame) -> None:
    events_path = output_path(config, "events", "midi_events.csv")
    events.to_csv(events_path, index=False)

    full_tracks = [_tempo_track(config)]
    for batch in config["stems"]:
        full_tracks.append(_stem_track(config, batch, events[events["batch"] == batch]))
    for batch in [batch for batch in events["batch"].unique() if batch not in config["stems"]]:
        full_tracks.append(_stem_track(config, batch, events[events["batch"] == batch]))
    _write_midi(output_path(config, "midi", "plant_music_full.mid"), config, full_tracks)

    for batch in list(config["stems"].keys()) + [batch for batch in events["batch"].unique() if batch not in config["stems"]]:
        tracks = [_tempo_track(config), _stem_track(config, batch, events[events["batch"] == batch])]
        _write_midi(output_path(config, "midi", f"{batch}_stem.mid"), config, tracks)
