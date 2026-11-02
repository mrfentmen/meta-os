#!/usr/bin/env python3
"""os-build/layer1/gen_transcripts.py -- BF4-03..06: the transcripts, verbatim.

Each section embeds the actual stdout of the program that ran, read from
os-build/layer1/host/build/<name>.log, plus what the transcript does and does not
prove. Nothing here is retyped: if a log is missing the section says MISSING and
the script exits non-zero, because a transcript document that quietly omits a
run is worse than no document.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "os-build", "layer1", "host", "build")
DEST = os.path.join(ROOT, "os-build", "layer1", "TRANSCRIPTS.md")

SECTIONS = [
    ("BF4-03", "tests/t52_supervisor",
     "The supervisor story: start, stop, and restart-on-crash of two services",
     "Two services (`a`, `b`) are registered, driven through the state machine, and "
     "restarted under each of the three restart policies. Every transition in the "
     "transcript is a call into `services/supervisor/supervisor.goose`; the crash is "
     "the test calling `sup_set_state(..., ST_FAILED)`.",
     "It does not prove a process was created, killed or restarted. `sys_spawn` and "
     "`sys_kill` are not declared anywhere in the corpus (see PROPOSALS.md P3), so what "
     "is proven is the DECISION the supervisor makes and the state it records, with no "
     "actor underneath it."),
    ("BF4-04", "tests/t50_logd",
     "The log service end to end: format, accept, flush, loss accounting",
     "The formatter's exact record shape, the ring accepting records, the flush draining "
     "them, and — the important one — the loss counter: a flood that overflows the ring "
     "must report dropped records rather than silently discarding them.",
     "The flush writes through `sys_write_serial`, which on this host is the terminal. "
     "It does not prove a kernel log sink, and it does not prove rotation — that is the "
     "next transcript."),
    ("BF4-04", "tests/t71_rotate",
     "Log rotation and retention: roll on bytes, keep newest, count every drop",
     "`services/logd/rotate.goose` driven for the first time: segments roll on a byte "
     "budget, a new day never appends to yesterday's open segment, retention drops the "
     "oldest and never the newest, `keep 0` means no limit rather than delete "
     "everything, a full segment list refuses with `E_NOROOM` instead of deciding to "
     "discard history, and the day shape is checked against a calendar (including the "
     "2024 leap day rather than a value computed by the function under test).",
     "It does not prove that a segment name maps to a file with those bytes in it. "
     "Nothing in this corpus writes a segment to the filesystem yet; that mapping is "
     "NOT BUILT."),
    ("BF4-05", "tests/t54_storage",
     "The storage contract against the RAM backend",
     "Write, read, overwrite, out-of-range refusal (both ends, both directions, no "
     "silent clamp), the write counter, seal, and read-after-seal. The backend reports "
     "itself volatile, which is the one property a caller has to be told rather than "
     "guess.",
     "It does not prove persistence. The backend is RAM by design (DESIGN.md §7): the "
     "contents survive a remount *within one process* and nothing else. Quota is a "
     "block count, not an accounting system — the filesystem's own quota behaviour is "
     "in the t65 transcript."),
    ("BF4-06", "tests/t66_shell",
     "The shell against the real filesystem service",
     "The `cat`, `cp`, `rm` and `ls` builtins run against `services/fs` (not against a "
     "stub), scripts are created as real files, executed line by line, and a failing "
     "line stops the script and is named in the error. `ps`, `uptime`, `log`, `audit` "
     "and `time` are exercised through the registry the test populates.",
     "It does not prove a console. Input arrives as strings handed to the shell, not as "
     "key events from `sys_read_key`, and the output goes to the serial shim. The "
     "parser hardening cases are in this same file; they are line-parser cases, not "
     "terminal ones."),
    ("BF4-15", "tests/t68_proto",
     "The network protocol pack, pairwise: ARP, ICMP, UDP and the TCP state machine",
     "The four protocol modules talk to each other through `tests/harness/link.goose`, an "
     "in-memory link that carries real frames: an ARP request is built, queued, drained, "
     "parsed by the other side, answered, and the answer is parsed back; an echo request "
     "is replied to with the same sequence and payload and a reply with another sequence "
     "is rejected; a datagram survives the round trip with its checksum verified and a "
     "single flipped byte is refused; the TCP machine is driven through active open, "
     "passive open, SYN/SYN-ACK, established, FIN and TIME_WAIT, with a dropped send, the "
     "loss counter, the retransmit timer, the doubled backoff, and a reordered packet "
     "delivered in order.",
     "Nothing here touches a wire. `sys_net_send` and `sys_net_recv` are refused by the "
     "host shim (SERVICE_RUNS.md), so the link is the test's own buffer: the bytes are "
     "real and the framing is real, but no NIC, no driver and no kernel are involved. It "
     "also proves nothing about interoperability with a real peer: every packet is "
     "produced and consumed by this same corpus, so a shared misunderstanding of a "
     "header would pass every check."),
    ("BF5-04", "tests/t75_supervisor_load",
     "The supervisor under load: ten services, three policies, a crash budget, the table quota",
     "Ten services registered as a dependency chain and started in order, then crashed under "
     "`RP_ON_FAIL` (restart with a backoff), `RP_NEVER` (give up, stay failed), `RP_ALWAYS` on a "
     "clean exit (restart at once, budget untouched), a service that exhausts a budget of two "
     "restarts, a long uptime that clears the budget, and registration past the table's capacity "
     "refusing with `E_NOROOM` while the ten already registered stay untouched.",
     "No process was spawned or killed. `sys_spawn`/`sys_kill` do not exist (PROPOSALS.md P3), so "
     "a restart here is the slot moving RESTARTING -> STARTING and a caller being told to spawn. "
     "It proves the policy and the bookkeeping, not the actor."),
    ("BF5-05", "tests/t76_demo_session",
     "The demo session: the shell service driving the commands the demo speaks",
     "A real session against `services/fs`: format, `/etc/hostname`, `/motd`, three registered "
     "services, then `help`, `pwd`, `ls`, `cat`, `mkdir`, `cd`, `echo`, `ps`, `uptime`, `log`, "
     "`audit`, `time`, plus three refusals a demo should show (`cat nope`, a pipeline, an unknown "
     "command). The prompts and output are the shell's own; `DEMO_SHELL.md` reads this output.",
     "The lines were handed to `sh_exec`, not typed: `sh_run` reads `sys_read_key`, which the host "
     "shim answers with \"nothing pending\" forever (that is the `console` hang in "
     "BOOT_REHEARSAL.md). It also does not prove the kernel's shell prints the same words — see "
     "the alignment table in DEMO_SHELL.md, which is unverified on this checkout."),
    ("B1/D4", "tests/t77_gaps",
     "The four services that had no driver: devices, session, socket, timesync",
     "Each of the four is imported and driven for the first time: `devices` through its "
     "kind/slot/name refusals, its state machine and a table filled past `DEV_MAX`; "
     "`devices/hotplug` through a queue overflow where `delivered + dropped` must equal "
     "`raised`; `session` through the login flow from keystrokes to a resolvable session, "
     "then a table filled past `SES_CAP`; `socket` through bind, send, the two-datagram "
     "queue and a closed handle; `timesync` through eight malformed replies and the "
     "smear, which must close its gap without overshooting.",
     "It did not find the code clean: `login_submit` opened sessions with `user_id = 0` "
     "and could not log a user in at all, `hotplug` counted deliveries on raise and could "
     "report more delivered than raised, and the NTP fraction scaling truncated the "
     "sub-second field. All three are fixed and this transcript is the post-fix output. "
     "It does not prove any of these services can be started: four services, still "
     "libraries, still no caller."),
    ("BF4-16", "tests/t65_fs",
     "MOSFS01 edge cases: full disk, hostile paths, the checker",
     "Format, mount, files, directories, remount, the hostile path set (`..`, "
     "repeated slashes, overlong components, trailing slash on a file), the fsck "
     "checker on a clean tree, on a planted leak, and after a repair, then a loop that "
     "fills the data region until the allocator refuses.",
     "It does not prove crash safety: nothing interrupts a write, and there is no "
     "journal. It also cannot prove persistence across processes, because the backend "
     "is RAM."),
]


def read_log(name):
    # The runner names its logs after the source file's basename, not its path:
    # tests/t52_supervisor -> host/build/t52_supervisor.log.
    path = os.path.join(OUT, name.split("/")[-1] + ".log")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return fh.read().rstrip("\n")


def main():
    missing = []
    L = []
    A = L.append
    A("# Transcripts, verbatim (BF4-03 to BF4-06, BF4-15, BF4-16, BF5-04, BF5-05, and the four services that had none)")
    A("")
    A("Generated by `os-build/layer1/gen_transcripts.py` from")
    A("`os-build/layer1/host/build/*.log`. The text inside each block is the program's")
    A("own stdout, unedited — every `ok` line below was printed by a process that ran,")
    A("built from `services/` by Goose and clang on this Mac. Regenerate with:")
    A("")
    A("```")
    A("./os-build/layer1/run_native.sh && python3 os-build/layer1/gen_transcripts.py")
    A("```")
    A("")
    A("The full pass/fail table for every program is `SERVICE_RUNS.md`; this file exists")
    A("because a table of pass counts is not a transcript, and a task that asks for a")
    A("transcript is asking to see the checks.")
    A("")

    for task, name, title, proves, not_proves in SECTIONS:
        body = read_log(name)
        A("## %s — %s" % (task, title))
        A("")
        A("`%s`" % name)
        A("")
        A("**What this run proves.** " + proves)
        A("")
        A("**What it does not.** " + not_proves)
        A("")
        if body is None:
            missing.append(name)
            A("**TRANSCRIPT MISSING** — `%s.log` was not found. Run "
              "`./os-build/layer1/run_native.sh %s` and regenerate." % (name, name.split("/")[-1]))
            A("")
            continue
        A("```")
        A(body)
        A("```")
        A("")

    A("## The refusal that makes these transcripts evidence")
    A("")
    A("`os-build/layer1/host/host_shim.c` implements the ten `sys_*` externs and")
    A("**refuses five on purpose**: `sys_spawn`, `sys_kill`, `sys_net_send`,")
    A("`sys_net_recv` return a failure code, and `sys_read_key` reports \"nothing")
    A("pending\". A shim that faked those would make every transcript above green for a")
    A("reason that does not exist on the kernel. The refusal is the honest part.")
    A("")
    A("## Reproduce, on this machine")
    A("")
    A("```")
    A("./os-build/layer1/run_native.sh            # every program, with pass/fail per test")
    A("./os-build/layer1/check_services.sh        # typecheck every root and every test")
    A("```")
    A("")
    A("Neither command boots anything. There is no kernel in this loop: the run is a host")
    A("process with a substituted syscall surface, and that is the whole claim.")

    with open(DEST, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")

    if missing:
        print("MISSING transcripts: " + ", ".join(missing))
        return 1
    print("transcripts: %d sections -> %s" % (len(SECTIONS), os.path.relpath(DEST, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
