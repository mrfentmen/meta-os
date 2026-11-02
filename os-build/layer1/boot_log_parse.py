#!/usr/bin/env python3
"""boot_log_parse.py — turn a serial log into structured records.

Eyeballing two boot logs to find what changed is how a regression gets missed. This
parses the line shapes the kernel actually emits into a JSON object, so a comparison is
structural instead of textual.

Shapes recognised (from kernel/src/main.rs, user.rs, sched.rs, interrupts.rs):

  meta--         "META OS 0.1 (K6)", "META OS KERNEL - alive (K1)", "META OS KERNEL - panic"
  memory         "mem map: 15 regions ...", "mem frames: N usable total",
                 "mem heap: 512K total", "mem stress 10k ok, heap free ...", "mem summary: K4 up"
  userspace      "user <name>: <n> bytes ...", "HELLO FROM USERSPACE", "<name>: ...",
                 "user exit code N", "user bad syscall N refused", "INT user page-fault ..."
  timer/keyboard "K3 timer: N ticks ...", "K3 keyboard: first scancode 0x..."
  shell          "STATUS tasks=N ticks=N heap_free_kb=N", "uptime Ns ticks N",
                 "mem frames_free N frames_total N ...", "ps id N state ..."
  panic          "panicked at <file>:<line>:", next line is the message message

Unknown lines are counted, not dropped silently: `unparsed` lists them (capped).

Usage: boot_log_parse.py <log> [--json] [--out path]
Exit: 0 parsed (some unparsed lines are normal), 2 missing file.
"""

import json
import pathlib
import re
import sys

PATTERNS = [
    ("alive", re.compile(r"^META OS KERNEL - alive \(K1\)$")),
    ("banner", re.compile(r"^META OS 0\.1 \(K6\)$")),
    ("panic_banner", re.compile(r"^META OS KERNEL - panic$")),
    ("mem_map", re.compile(r"^mem map: (\d+) regions, usable (\d+)K")),
    ("mem_frames", re.compile(r"^mem frames: (\d+) usable total")),
    ("mem_heap", re.compile(r"^mem heap: (\d+)K total")),
    ("mem_summary", re.compile(r"^mem summary: (\w+) up")),
    ("user_load", re.compile(r"^user (\w+): (\d+) bytes magic=(\S+)")),
    ("user_exit", re.compile(r"^user exit code (\d+)")),
    ("user_refused", re.compile(r"^user bad syscall (\d+) refused")),
    ("user_fault", re.compile(r"^INT user page-fault addr (\S+) err (\S+): task killed")),
    ("timer", re.compile(r"^K3 timer: (\d+) ticks")),
    ("keyboard", re.compile(r"^K3 keyboard: first scancode (0x[0-9a-f]+)")),
    ("status", re.compile(r"^STATUS tasks=(\d+) ticks=(\d+) heap_free_kb=(\d+)")),
    ("uptime", re.compile(r"^uptime (\d+)s ticks (\d+)")),
    ("ps", re.compile(r"^ps id (\d+) state (\w+)")),
    ("panic_at", re.compile(r"^panicked at (.+):(\d+):(\d+):")),
]


def parse(text):
    out = {"alive": False, "banner": False, "panic": False, "memory": {},
           "userspace": {"loads": [], "exits": [], "refused": [], "faults": []},
           "timer": None, "keyboard": None, "shell": [], "panic_detail": None,
           "counts": {}, "unparsed": []}
    lines = text.splitlines()
    for index, line in enumerate(lines):
        matched = False
        for name, pattern in PATTERNS:
            match = pattern.match(line)
            if not match:
                continue
            matched = True
            out["counts"][name] = out["counts"].get(name, 0) + 1
            if name == "alive":
                out["alive"] = True
            elif name == "banner":
                out["banner"] = True
            elif name == "panic_banner":
                out["panic"] = True
            elif name == "mem_map":
                out["memory"]["regions"] = int(match.group(1))
                out["memory"]["usable_kb"] = int(match.group(2))
            elif name == "mem_frames":
                out["memory"]["frames"] = int(match.group(1))
            elif name == "mem_heap":
                out["memory"]["heap_kb"] = int(match.group(1))
            elif name == "mem_summary":
                out["memory"]["summary"] = match.group(1)
            elif name == "user_load":
                out["userspace"]["loads"].append(
                    {"name": match.group(1), "bytes": int(match.group(2))})
            elif name == "user_exit":
                out["userspace"]["exits"].append(int(match.group(1)))
            elif name == "user_refused":
                out["userspace"]["refused"].append(int(match.group(1)))
            elif name == "user_fault":
                out["userspace"]["faults"].append(
                    {"addr": match.group(1), "err": match.group(2)})
            elif name == "timer":
                out["timer"] = int(match.group(1))
            elif name == "keyboard":
                out["keyboard"] = match.group(1)
            elif name in ("status", "uptime", "ps"):
                out["shell"].append({"kind": name, "line": line})
            elif name == "panic_at":
                out["panic_detail"] = {
                    "file": match.group(1), "line": int(match.group(2)),
                    "message": lines[index + 1].strip() if index + 1 < len(lines) else "",
                }
            break
        if not matched and line.strip():
            if len(out["unparsed"]) < 40:
                out["unparsed"].append(line)
    return out


def main(argv):
    if len(argv) < 1:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    path = pathlib.Path(argv[0])
    if not path.is_file():
        print(f"boot_log_parse: missing {path}", file=sys.stderr)
        return 2
    parsed = parse(path.read_text(errors="replace"))
    parsed["source"] = str(path)
    if "--out" in argv:
        target = pathlib.Path(argv[argv.index("--out") + 1])
        target.write_text(json.dumps(parsed, indent=2) + "\n")
        print(f"boot_log_parse: wrote {target}")
    if "--json" in argv or "--out" not in argv:
        print(json.dumps(parsed, indent=2))
    else:
        print(f"boot_log_parse: {path.name}: alive={parsed['alive']} "
              f"frames={parsed['memory'].get('frames')} "
              f"loads={[l['name'] for l in parsed['userspace']['loads']]} "
              f"timer={parsed['timer']} keyboard={parsed['keyboard']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
