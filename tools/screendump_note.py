"""screendump_note.py — emit the Markdown proof note for a screendump.

Names and values only; no image bytes, no claims the log does not
support. Missing values render as `—`.
"""

from __future__ import annotations

import sys


def note(filename: str, parsed: dict) -> str:
    ticks = parsed.get("ticks") or []
    tick_text = f"{ticks[0]}..{ticks[-1]}" if ticks else "—"
    return "\n".join(
        [
            f"**Proof note — `{filename}`**",
            "",
            f"- Banner: {parsed.get('banner') or '—'}",
            f"- Alive: {'yes' if parsed.get('alive') else 'no'}",
            f"- Panics: {parsed.get('panic_count', 0)}",
            f"- Ticks: {tick_text}",
            f"- Verdict: {parsed.get('verdict', '—')}",
        ]
    ) + "\n"


def main(filename: str, log_path: str) -> int:
    from bootlog_parse import parse_file

    sys.stdout.write(note(filename, parse_file(log_path)))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: screendump_note.py <screendump-name> <serial-log>")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
