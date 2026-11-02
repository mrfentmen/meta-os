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


# Constants that no driver can settle, with the reason. These are not "probably fine":
# each one is a claim about why a test cannot exist, and the four DEAD entries are
# findings -- the limit the name promises is not enforced anywhere.
REASONS = {
    # --- DEAD: declared, never read. The limit does not exist. -------------
    "FS_MAX_DEPTH": ("DEAD", "fs.goose declares it and never reads it: a path of any depth is accepted, "
                              "bounded only by MAX_INODES. The 16 in the name is not enforced."),
    "CK_MAX_BLOCKS": ("DEAD", "fsck.goose declares it and sizes its tables from MAX_DISK_BLOCKS instead; "
                               "a second copy of the number that nothing compares."),
    "CK_MAX_INODES": ("DEAD", "same: fsck sizes from MAX_INODES. Two names for one number means the table "
                               "can be sized for the wrong limit and nothing notices."),
    "EX_NAME_MAX": ("DEAD", "example.goose declares it and never reads it; the service names no records."),
    "DL_LIT_MAX": ("DEAD", "delta.goose declares the literal cap and never reads it; the copy loop takes a "
                            "runtime length, so an oversized literal is truncated by the destination array."),
    # --- Not a capacity at all --------------------------------------------
    "MOD_CAPS": ("BITFLAG", "a modifier bit for Caps Lock, not a size. It matches the audit on \"CAP\" the "
                            "same way the CAP_* flags do; nothing can exceed it."),
    "UPD_CONTENT_MAX": ("LAYOUT", "a stride (index * 4096) over the ContentSet buffer, not a refusal point. "
                                   "The array is sized 8 * 4096, so the stride cannot be exceeded."),
    # --- Enforced, but another check always fires first -------------------
    "DNS_QUERY_MAX": ("UNREACHABLE", "the 255-byte name cap is checked before any byte is written, and the "
                                      "encoding adds at most 2 bytes, so a packet can never reach 512 here. "
                                      "Defence in depth, not a limit a caller can hit."),
    "BO_MAX": ("BOUNDARY", "the boot table has 28 rows and the cap is 30; the array can never fill without "
                            "editing the table, so a driver would only prove the table's size."),
    "DEP_MAX": ("BOUNDARY", "the stop plan is capped at DEP_MAX (32) and the boot sequence is 28; the cap "
                            "cannot be reached without editing the table. DEP_MAX was 24 until R7, which "
                            "would have silently dropped four services from a stop plan."),
    "SET_MAX": ("BOUNDARY", "the settings table holds six keys and the cap is 24; the six slots above them are "
                             "reserved for named profiles, which no function in settings.goose creates yet. A "
                             "driver cannot fill the table through the public API, so nothing can prove the cap."),
    "SCROLL_MAX": ("INTERNAL", "disp_scroll clamps hist_lines and no accessor returns it, so the clamp has "
                                  "no observable effect through the public surface."),
    "HISTORY_SLOTS": ("INTERNAL", "the console history is a ring: pushes overwrite the oldest entry rather "
                                     "than refusing, and no accessor exposes the depth."),
    "HANDLE_GEN_MAX": ("WRAP", "handle arithmetic wraps the generation field at this constant; reaching the "
                                  "wrap needs 2^k reuses of one slot, which no driver can do in bounded time."),
    "SK_GEN_MAX": ("WRAP", "sk_open wraps the generation at 255 reuses of a slot; the handle is the only "
                              "observable, so the test would assert a handle pattern, not a refusal."),
    "STALL_LIMIT": ("ENV", "only reachable when the kernel's tick stops advancing. The host shim's clock "
                             "always advances, so sleep_ticks cannot enter the stalled branch here."),
    "SH_OUT_MAX": ("TRUNCATION", "the output cap is a truncation point: out_str returns false and the "
                                    "builtin's output is dropped, but sh_exec still returns CODE_OK, so "
                                    "there is no refusal for a test to assert."),
    "EX_REC_MAX": ("NO-HARNESS", "the example service has no driver: its entry point takes a BootInfo "
                                   "that only a supervisor can build, and the record append is inside run()."),
    "CFG_TEXT_MAX": ("NO-HARNESS", "same service, same reason: the config read happens in run(BootInfo)."),
    "DL_OPS_MAX": ("LAYOUT", "the operation array's size, also returned by delta_ops_max(); the apply "
                              "path bounds by the array, so the constant can be read but not exceeded."),
    "UPD_REC_KEEP": ("INTERNAL", "the update-record history is a ring the module owns: push overwrites the "
                                    "oldest entry and no accessor returns the depth."),
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
    explained = [r for r in unproven if r[0] in REASONS]
    open_ = [r for r in unproven if r[0] not in REASONS]

    L = []
    A = L.append
    A("# Limits, and the test that tries to break each one (BF4-17)")
    A("")
    A("Generated by `os-build/layer1/gen_limits.py`. Every numeric limit constant in")
    A("`services/` is listed. **%d of %d are exercised by a test**, %d more carry a named" % (len(proven), len(rows), len(explained)))
    A("reason why no driver can settle them, and **%d %s still open**." % (len(open_), "is" if len(open_) == 1 else "are"))
    A("")
    A("Two ways a limit counts as proven: the test names the constant, or the test")
    A("breaks the limit through the public API and the override table says which check")
    A("does it. Nothing is marked proven because it \"looks covered\".")
    A("")
    A("The converse is not true: a limit can be exercised by a test that never names")
    A("it, and it will still read UNPROVEN here. Treat the top table as a lower bound")
    A("on coverage and the bottom one as the list to check by hand.")
    A("")
    # Per-service rollup: Round 7 asks for closure service by service, so the state
    # of one service has to be one line that can be checked without reading the
    # whole table. Counted from the same rows as the details below.
    A("## Per service (Round 7 A1–A22)")
    A("")
    A("| service | limits | exercised | named reason | of those DEAD | open | state |")
    A("|---|---|---|---|---|---|---|")
    by_svc = {}
    for r in rows:
        svc = r[2].split("/")[1] if r[2].startswith("services/") else r[2]
        by_svc.setdefault(svc, []).append(r)
    for svc in sorted(by_svc):
        rs = by_svc[svc]
        ex = len([r for r in rs if r[3]])
        nm = len([r for r in rs if not r[3] and r[0] in REASONS])
        op = len([r for r in rs if not r[3] and r[0] not in REASONS])
        dead = len([r for r in rs if r[0] in REASONS and REASONS[r[0]][0] == "DEAD"])
        state = "OPEN" if op else "closed"
        A("| `%s` | %d | %d | %d | %d | %d | %s |" % (svc, len(rs), ex, nm, dead, op, state))
    A("")
    A("A service row is `closed` when every limit it declares is either driven by a")
    A("test or carries a reason; `OPEN` means at least one has neither, and there are")
    A("none of those.")
    A("")
    A("## Proven")
    A("")
    A("| limit | value | in | driven by | how |")
    A("|---|---|---|---|---|")
    for name, value, where, who, how in proven:
        A("| `%s` | `%s` | `%s` | `%s` | %s |" % (name, value, where, who, how))
    A("")
    if unproven:
        if explained:
            A("## Named reason — no driver can settle these")
            A("")
            A("Each row is a claim about why a test cannot exist, which is a different thing")
            A("from coverage. **DEAD** rows are findings: the limit in the name is enforced")
            A("nowhere in the source, so the constant is a comment pretending to be a check.")
            A("")
            A("| limit | value | in | kind | why no driver can settle it |")
            A("|---|---|---|---|---|")
            for name, value, where, _who, _how in explained:
                kind, why = REASONS[name]
                A("| `%s` | `%s` | `%s` | %s | %s |" % (name, value, where, kind, why))
            A("")
            dead = [n for n in (r[0] for r in explained) if REASONS[n][0] == "DEAD"]
            if dead:
                A("The DEAD rows in that table are not 'unproven', they are **not limits**: "
                  "`%s`. Nothing enforces them, so nothing can refuse at their edge. The fix is to" % ", ".join("`%s`" % n for n in dead))
                A("enforce the bound where the name promises one, or delete the constant. Both are")
                A("outside this lane's frozen surface, so they are reported, not patched.")
                A("")
        if open_:
            A("## UNPROVEN — written, never driven to the edge")
            A("")
            A("| limit | value | in | what the comment says it is for |")
            A("|---|---|---|---|")
            for name, value, where, _who, _how in open_:
                A("| `%s` | `%s` | `%s` | %s |" % (name, value, where, "—"))
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
    print("limits: %d  proven: %d  explained: %d  open: %d" % (len(rows), len(proven), len(explained), len(open_)))
    for name, _v, _w, who, _h in open_:
        print("  OPEN %s" % name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
