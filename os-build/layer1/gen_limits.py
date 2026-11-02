#!/usr/bin/env python3
"""os-build/layer1/gen_limits.py -- BF4-17: every limit, and the test that breaks it.

Scans `services/` for numeric limit constants (MAX / SLOTS / BUDGET / CAP /
LIMIT / HIGH_WATER), then looks for a test that names the constant. A limit with
no test is reported as UNPROVEN, which is the honest reading: green tests
elsewhere do not exercise it.

Overrides are the cases a name search misses: tests that break a limit through a
public function without ever naming its constant. Each one is listed with the
check that proves it, so the claim stays auditable.
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


def main():
    tests = test_files()
    rows = []
    for name, value, where, comment in limit_constants():
        who = find_named(name, tests)
        if who:
            rows.append((name, value, where, who, "names the constant"))
        elif name in OVERRIDES:
            rows.append((name, value, where, OVERRIDES[name][0], OVERRIDES[name][1]))
        else:
            rows.append((name, value, where, None, None))

    proven = [r for r in rows if r[3]]
    unproven = [r for r in rows if not r[3]]

    L = []
    A = L.append
    A("# Limits, and the test that tries to break each one (BF4-17)")
    A("")
    A("Generated by `os-build/layer1/gen_limits.py`. Every numeric limit constant in")
    A("`services/` is listed. **%d of %d are exercised by a test.** The rest are marked" % (len(proven), len(rows)))
    A("UNPROVEN, which means exactly that: the code that enforces the limit is written")
    A("and has never been driven to its edge. A green suite elsewhere says nothing")
    A("about a specific limit.")
    A("")
    A("Two ways a limit counts as proven: the test names the constant, or the test")
    A("breaks the limit through the public API and the override table says which check")
    A("does it. Nothing is marked proven because it \"looks covered\".")
    A("")
    A("The converse is not true: a limit can be exercised by a test that never names")
    A("it, and it will still read UNPROVEN here. Treat the top table as a lower bound")
    A("on coverage and the bottom one as the list to check by hand.")
    A("")
    A("## Proven")
    A("")
    A("| limit | value | in | driven by | how |")
    A("|---|---|---|---|---|")
    for name, value, where, who, how in proven:
        A("| `%s` | `%s` | `%s` | `%s` | %s |" % (name, value, where, who, how))
    A("")
    if unproven:
        A("## UNPROVEN — written, never driven to the edge")
        A("")
        A("| limit | value | in | what the comment says it is for |")
        A("|---|---|---|---|")
        for name, value, where, _who, _how in unproven:
            A("| `%s` | `%s` | `%s` | %s |" % (name, value, where, comment or "—"))
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
    print("limits: %d  proven: %d  unproven: %d" % (len(rows), len(proven), len(unproven)))
    for name, _v, _w, who, _h in unproven:
        print("  UNPROVEN %s" % name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
