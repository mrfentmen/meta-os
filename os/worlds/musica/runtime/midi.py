"""musica MIDI export (HN-048).

Wires the adopted tool pretty_midi (MIT, HN-046) into the loop:
for each keeper take, the loop's own note events (melody + bass,
as rendered -- see compose.render_samples) are written as a real
MIDI file next to the keeper audio. The take record gains
midi_file (take-log format), the catalogue entry gains midi_file,
and midi.json manifests the tool and the files.

Dependency: pretty_midi (pip install pretty_midi). The Mac gate
needs it installed too; without it this stage fails loudly
instead of writing a fake MIDI file.

  python3 midi.py SESSION_DIR
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compose import render_samples  # noqa: E402
from take_log import read_log  # noqa: E402

MELODY_PROGRAM = 80  # Lead 1 (square)
BASS_PROGRAM = 38  # Synth Bass 1


def tool_version():
    try:
        from importlib.metadata import version
        return version("pretty_midi")
    except Exception:
        return "unknown"


def export_session_midi(session_dir):
    """Export MIDI for every keeper take. Returns the manifest."""
    import pretty_midi
    log_path = os.path.join(session_dir, "take_log.jsonl")
    takes = read_log(log_path)
    midi_dir = os.path.join(session_dir, "midi")
    os.makedirs(midi_dir, exist_ok=True)
    entries = []
    for take in takes:
        if take["verdict"] != "keeper":
            continue
        _samples, events = render_samples(take["params"], take["seed"])
        midi = pretty_midi.PrettyMIDI()
        melody = pretty_midi.Instrument(program=MELODY_PROGRAM)
        bass = pretty_midi.Instrument(program=BASS_PROGRAM)
        for event in events:
            note = pretty_midi.Note(
                velocity=90 if event["kind"] == "melody" else 100,
                pitch=event["midi"],
                start=event["start_s"],
                end=event["start_s"] + event["duration_s"])
            if event["kind"] == "melody":
                melody.notes.append(note)
            else:
                bass.notes.append(note)
        midi.instruments.append(melody)
        midi.instruments.append(bass)
        name = "%s.mid" % take["take_id"]
        midi.write(os.path.join(midi_dir, name))
        take["midi_file"] = "midi/%s" % name
        entries.append({"take_id": take["take_id"], "file": take["midi_file"],
                        "melody_notes": len(melody.notes),
                        "bass_notes": len(bass.notes)})
    with open(log_path, "w", encoding="utf-8") as fh:
        for take in takes:
            fh.write(json.dumps(take, sort_keys=True) + "\n")
    catalogue_path = os.path.join(session_dir, "catalogue.json")
    if os.path.exists(catalogue_path):
        with open(catalogue_path, encoding="utf-8") as fh:
            catalogue = json.load(fh)
        by_take = {e["take_id"]: e["file"] for e in entries}
        for track in catalogue.get("tracks", []):
            if track["take_id"] in by_take:
                track["midi_file"] = by_take[track["take_id"]]
        with open(catalogue_path, "w", encoding="utf-8") as fh:
            json.dump(catalogue, fh, indent=2, sort_keys=True)
    manifest = {"tool": "pretty_midi", "tool_version": tool_version(),
                "licence": "MIT", "takes": entries}
    with open(os.path.join(session_dir, "midi.json"), "w",
              encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
    return manifest


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Musica MIDI export")
    parser.add_argument("session_dir")
    args = parser.parse_args(argv)
    manifest = export_session_midi(args.session_dir)
    print("midi exported takes=%d tool=pretty_midi"
          % len(manifest["takes"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
