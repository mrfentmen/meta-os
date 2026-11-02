#!/usr/bin/env python3
"""os-build/layer1/gen_limits.py -- BF4-17: every limit, and the test that breaks it.

Scans `services/` for numeric limit constants (MAX / SLOTS / BUDGET / CAP / LIMIT /
HIGH_WATER), then looks for a test that names or drives the constant.

Three outcomes, and they are different claims:
  PROVEN        a test reaches the code that enforces the limit with a value past it.
  NOT A LIMIT   a bit flag (MOD_CAPS), or a constant whose name appears nowhere else --
                no code path can exceed it, so no test could prove anything.
  UNREACHABLE   a real limit that no host-side driver can reach; each carries the reason.
Anything else is UNPROVEN, which is the honest reading: the code is written and has never
been driven to its edge.

Overrides are the cases a name search misses: tests that break a limit through a public
function without ever naming its constant. Each one lists the check that proves it, so the
claim stays auditable.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SERVICES = os.path.join(ROOT, "services")
DEST = os.path.join(ROOT, "os-build", "layer1", "LIMITS.md")

LIMIT = re.compile(r"^let\s+([A-Z][A-Z0-9_]*):\s*i64\s*=\s*([^;]+);(.*)$", re.M)
KEYWORDS = ("MAX", "SLOTS", "BUDGET", "CAP", "LIMIT", "HIGH_WATER", "QUOTA", "KEEP")

# constant -> (test file, what the test does). Only for limits whose test breaks
# them through an API instead of naming the constant.
OVERRIDES = {
    "ARG_MAX": ("tests/t73_shell_hard", "nine arguments refused, argv emptied (E_NOROOM)"),
    "ARG_TEXT_MAX": ("tests/t73_shell_hard", "193 bytes refused, 192 accepted; escapes counted unescaped"),
    "INI_TEXT_MAX": ("tests/t47_cfg", "values past the text cap refuse rather than truncate"),
    "ROT_SEG_MAX": ("tests/t71_rotate", "a ninth segment refuses with E_NOROOM and changes nothing"),
    "SLOTS": ("tests/t50_logd", "a flood drops records and the loss is counted"),
    "HIGH_WATER": ("tests/t50_logd", "flush decisions follow the high-water mark"),
    "FRAME_MAX": ("tests/t68_proto", "a frame over the cap is refused at the builder"),
    "ARP_SLOTS": ("tests/t68_proto", "the ARP table's slots are filled and the next insert is refused"),
    "LINK_SLOTS": ("tests/t68_proto", "the queue accepts LINK_SLOTS packets, then E_BUSY, nothing dropped"),
    "RTO_MAX_MS": ("tests/t68_proto", "backoff grows and is capped"),
    "SH_LINE_MAX": ("tests/t66_shell", "a line past the shell's buffer is refused"),
    "TAG_MAX": ("tests/t50_logd", "a tag past 8 bytes is refused"),
    "MSG_MAX": ("tests/t50_logd", "a message past 160 bytes is refused"),
    "LINE_MAX": ("tests/t50_logd", "a formatted record that would pass LINE_MAX is refused"),
    "VCON_MAX": ("tests/t56_input_display", "the virtual consoles fill and the next one is E_NOROOM"),
    "DISPLAY_LINE_MAX": ("tests/t56_input_display", "a line wider than the console is refused"),
    "AH_CAP": ("tests/t59_agenthost", "the agent table fills and the next registration is refused"),
    "AUD_REC_BUDGET": ("tests/t60_audit", "a record past the budget is refused, not truncated"),
    "FS_MAX_INODES": ("tests/t65_fs", "the inode table is exhausted and create refuses"),
    "MAX_FILE_BLOCKS": ("tests/t65_fs", "a file past five blocks is refused, five fit exactly"),
    "MAX_NAME": ("tests/t65_fs", "a 13-byte name component is refused"),
    "ROT_NAME_MAX": ("tests/t71_rotate", "a 4-byte buffer refuses a 30-byte name and writes nothing"),
}

# Bit flags matched by the CAP heuristic. A flag is not a size and cannot be exceeded.
FLAGS = {"MOD_CAPS"}

# Real limits whose edge no host-side driver can cross. Each reason names the structural
# bound, so a reader can check the claim rather than trust the label.
UNREACHABLE = {
    "SET_MAX": "the settings table holds 24 entries, but only seven ids exist (SK_MAX_ID) and st_import refuses any other id, so no input can fill the table",
    "SH_OUT_MAX": "the cap is supplied by the caller to sh_exec; no in-tree command emits 4096 bytes, and a smaller caller cap is a different limit",
    "EX_REC_MAX": "a tick record is bounded by its own fields (about 45 bytes at the widest timestamp), so the 128-byte build cap cannot be reached",
    "CFG_TEXT_MAX": "the cap is the read size handed to fs_read; the filesystem's block and read caps are driven by t65, and load_config cannot exceed its own buffer",
    "DL_OPS_MAX": "DeltaFile.ops is a fixed [..4] array, so nops cannot exceed the constant the array was declared from; the type is the enforcement",
    "DNS_QUERY_MAX": "an encoded name is at most 255 bytes plus a five-byte tail (DNS_NAME_MAX is driven by t79), so a 512-byte query cannot overflow; the check is defensive",
    "DEP_MAX": "the boot table holds 29 services (BO_MAX - 1); deps_stop_plan can never produce its 32nd entry, and its output array is [..32]",
    "STALL_LIMIT": "reached only by a frozen kernel clock; the host shim's clock advances, so this needs the kernel test, not a host driver",
}


def limit_constants():
    out = []
    for base, _dirs, files in os.walk(SERVICES):
        for f in sorted(files):
            if not f.endswith(".goose") or f.startswith("."):
                continue
            path = os.path.join(base, f)
            rel = os.path.relpath(path, ROOT)
            if "/tests/" in rel:
                continue
            try:
                text = open(path, encoding="utf-8").read()
            except OSError:
                continue
            for name, value, rest in LIMIT.findall(text):
                if not any(k in name for k in KEYWORDS):
                    continue
                # E_* are error codes and CAP_* are capability BIT FLAGS: both match on
                # "CAP"/"LIMIT" by accident, and neither is a size a caller can exceed.
                if name.startswith("E_") or name.startswith("CAP_"):
                    continue
                comment = rest.strip()
                if comment.startswith("//"):
                    comment = comment[2:].strip()
                out.append((name, value.strip(), rel, comment))
    return out


def test_files():
    d = os.path.join(SERVICES, "tests")
    return [f for f in sorted(os.listdir(d)) if f.endswith(".goose")]


def find_named(name, tests):
    for tf in tests:
        text = open(os.path.join(SERVICES, "tests", tf), encoding="utf-8").read()
        if re.search(r"\b%s\b" % re.escape(name), text):
            return "tests/" + tf[:-6]
    return None


def occurrences(name):
    """How many times the name appears in service code (tests excluded).

    One means the declaration is the only mention: nothing reads it, so nothing can
    exceed it. That is a dead constant, not an unproven limit.
    """
    n = 0
    for base, _dirs, files in os.walk(SERVICES):
        if os.path.basename(base) == "tests":
            continue
        for f in files:
            if not f.endswith(".goose"):
                continue
            try:
                text = open(os.path.join(base, f), encoding="utf-8").read()
            except OSError:
                continue
            n += len(re.findall(r"\b%s\b" % re.escape(name), text))
    return n


def main():
    tests = test_files()
    rows = []
    for name, value, where, comment in limit_constants():
        who = None if name in FLAGS else find_named(name, tests)
        if who:
            rows.append((name, value, where, who, "names the constant"))
        elif name in OVERRIDES and name not in FLAGS:
            rows.append((name, value, where, OVERRIDES[name][0], OVERRIDES[name][1]))
        else:
            rows.append((name, value, where, None, None))

    proven, flags, dead, unreachable, unproven = [], [], [], [], []
    for r in rows:
        name = r[0]
        if name in FLAGS:
            flags.append(r)
        elif occurrences(name) <= 1:
            dead.append(r)
        elif name in UNREACHABLE:
            unreachable.append(r)
        elif r[3]:
            proven.append(r)
        else:
            unproven.append(r)

    L = []
    A = L.append
    A("# Limits, and the test that tries to break each one (BF4-17)")
    A("")
    A("Generated by `os-build/layer1/gen_limits.py`. Every numeric limit-like constant in")
    A("`services/` is listed. **%d of %d are exercised by a test**; %d are not limits at all"
      % (len(proven), len(rows), len(flags) + len(dead)))
    A("(bit flags or dead declarations), and %d are real limits no host driver can reach." % len(unreachable))
    A("**%d remain UNPROVEN.**" % len(unproven))
    A("")
    A("Three outcomes are different claims, and the table keeps them apart:")
    A("")
    A("- **Proven** — a test reaches the enforcing code with a value on the wrong side.")
    A("- **Not a limit** — a bit flag, or a constant nothing reads. No test could prove it,")
    A("  because there is no edge to cross.")
    A("- **Unreachable** — the code enforces it, but the host cannot produce the input. Each")
    A("  row names the structural bound so the claim can be checked.")
    A("")
    A("Nothing is marked proven because it \"looks covered\".")
    A("")
    A("## Proven")
    A("")
    A("| limit | value | in | driven by | how |")
    A("|---|---|---|---|---|")
    for name, value, where, who, how in proven:
        A("| `%s` | `%s` | `%s` | `%s` | %s |" % (name, value, where, who, how))
    A("")
    if flags or dead:
        A("## Not limits")
        A("")
        A("| constant | value | in | why it is not a limit |")
        A("|---|---|---|---|")
        for name, value, where, _who, _how in flags:
            A("| `%s` | `%s` | `%s` | a bit flag (`MOD_*`), matched by the CAP heuristic; no caller can exceed it |"
              % (name, value, where))
        for name, value, where, _who, _how in dead:
            A("| `%s` | `%s` | `%s` | declared and never read: the name appears only at its declaration |"
              % (name, value, where))
        A("")
    if unreachable:
        A("## Unreachable on the host")
        A("")
        A("| limit | value | in | why a host driver cannot reach it |")
        A("|---|---|---|---|")
        for name, value, where, _who, _how in unreachable:
            A("| `%s` | `%s` | `%s` | %s |" % (name, value, where, UNREACHABLE[name]))
        A("")
    if unproven:
        A("## UNPROVEN — written, never driven to the edge")
        A("")
        A("| limit | value | in |")
        A("|---|---|---|")
        for name, value, where, _who, _how in unproven:
            A("| `%s` | `%s` | `%s` |" % (name, value, where))
        A("")
        A("Each of these needs one test that asks for limit+1 and asserts the refusal.")
        A("Until then they are WRITTEN, and the report says so.")
        A("")
    A("## Why this document exists")
    A("")
    A("A quota test is the only kind of test that fails in a way nobody notices: the")
    A("code works at every size below the limit, so ordinary use passes, and the")
    A("failure only appears on the day the data is big enough — which is the day it")
    A("matters. Enumerating the limits is the cheap half; the table above is the half")
    A("that says which ones are still guesses.")

    with open(DEST, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("limits: %d  proven: %d  flags: %d  dead: %d  unreachable: %d  unproven: %d"
          % (len(rows), len(proven), len(flags), len(dead), len(unreachable), len(unproven)))
    for name, _v, _w, _who, _h in unproven:
        print("  UNPROVEN %s" % name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
