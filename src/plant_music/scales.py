from __future__ import annotations

NOTE_TO_PC = {"C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3, "E": 4, "F": 5, "F#": 6, "GB": 6, "G": 7, "G#": 8, "AB": 8, "A": 9, "A#": 10, "BB": 10, "B": 11}
PC_TO_NOTE = {0: "C", 1: "C#", 2: "D", 3: "D#", 4: "E", 5: "F", 6: "F#", 7: "G", 8: "G#", 9: "A", 10: "A#", 11: "B"}
MODES = {"minor_pentatonic": [0, 3, 5, 7, 10], "dorian": [0, 2, 3, 5, 7, 9, 10], "major_pentatonic": [0, 2, 4, 7, 9]}


def note_to_midi(note: str) -> int:
    note = note.strip().upper()
    if len(note) < 2:
        raise ValueError(f"Invalid note: {note}")
    if note[1] in {"#", "B"}:
        name = note[:2]
        octave = int(note[2:])
    else:
        name = note[0]
        octave = int(note[1:])
    return (octave + 1) * 12 + NOTE_TO_PC[name]


def midi_to_note(midi: int) -> str:
    return f"{PC_TO_NOTE[midi % 12]}{midi // 12 - 1}"


def pitch_classes(config: dict) -> list[int]:
    scale = config["scale"]
    if "allowed_pitch_classes" in scale:
        return [int(pc) % 12 for pc in scale["allowed_pitch_classes"]]
    root = NOTE_TO_PC[scale["root"].upper()]
    return [(root + interval) % 12 for interval in MODES[scale["mode"]]]


def legal_notes(config: dict, low_note: str, high_note: str) -> list[int]:
    low = note_to_midi(low_note)
    high = note_to_midi(high_note)
    pcs = set(pitch_classes(config))
    notes = [m for m in range(low, high + 1) if m % 12 in pcs]
    if not notes:
        raise ValueError(f"No legal notes between {low_note} and {high_note}")
    return notes


def nearest_index(notes: list[int], midi: int) -> int:
    return min(range(len(notes)), key=lambda i: abs(notes[i] - midi))
