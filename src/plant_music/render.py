from __future__ import annotations

import shutil
import subprocess
import wave

import numpy as np
import pandas as pd

from .config import output_path, resolve_path


def render_demo(config: dict) -> str:
    if not config.get("render", {}).get("enabled", False):
        return "Rendering disabled by config."
    fluidsynth = shutil.which("fluidsynth")
    soundfont = resolve_path(config, config["render"].get("soundfont", ""))
    midi_path = output_path(config, "midi", "plant_music_full.mid")
    wav_path = output_path(config, "audio", "plant_music_demo.wav")
    if not fluidsynth:
        _render_simple_synth(config)
        return "Rendered fallback sine-synth audio because fluidsynth is not installed."
    if not soundfont.exists():
        _render_simple_synth(config)
        return f"Rendered fallback sine-synth audio because SoundFont was not found at {soundfont}."
    command = [
        fluidsynth,
        "-ni",
        "-g",
        str(config["render"].get("gain", 1.8)),
        str(soundfont),
        str(midi_path),
        "-F",
        str(wav_path),
        "-r",
        str(config["render"].get("sample_rate", 44100)),
    ]
    subprocess.run(command, check=True)
    return f"Rendered audio: {wav_path}"


def _render_simple_synth(config: dict) -> None:
    events_path = output_path(config, "events", "midi_events.csv")
    wav_path = output_path(config, "audio", "plant_music_demo.wav")
    events = pd.read_csv(events_path)
    sample_rate = int(config["render"].get("sample_rate", 44100))
    bpm = int(config["timeline"]["bpm"])
    total_beats = int(config["timeline"]["bars"]) * int(config["timeline"]["beats_per_bar"])
    total_seconds = total_beats * 60.0 / bpm + 2.0
    audio = np.zeros(int(total_seconds * sample_rate), dtype=np.float32)
    gains = {"R1": 0.16, "R2": 0.13, "R3": 0.10}

    for _, event in events.iterrows():
        start = int(float(event["beat_start"]) * 60.0 / bpm * sample_rate)
        duration = max(0.05, float(event["beat_duration"]) * 60.0 / bpm)
        length = min(int(duration * sample_rate), len(audio) - start)
        if length <= 0:
            continue
        t = np.arange(length, dtype=np.float32) / sample_rate
        freq = 440.0 * (2.0 ** ((int(event["pitch_midi"]) - 69) / 12.0))
        velocity_gain = float(event["velocity"]) / 127.0
        stem_gain = gains.get(str(event["batch"]), 0.10)
        wave_data = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * freq * 2 * t)
        attack = max(1, int(0.012 * sample_rate))
        release = max(1, int(min(0.08, duration * 0.35) * sample_rate))
        envelope = np.ones(length, dtype=np.float32)
        envelope[: min(attack, length)] = np.linspace(0.0, 1.0, min(attack, length))
        envelope[-min(release, length):] *= np.linspace(1.0, 0.0, min(release, length))
        audio[start:start + length] += wave_data.astype(np.float32) * envelope * velocity_gain * stem_gain

    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    if peak > 0:
        audio = audio / peak * 0.88
    pcm = (audio * 32767).astype("<i2")
    with wave.open(str(wav_path), "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(sample_rate)
        fh.writeframes(pcm.tobytes())
