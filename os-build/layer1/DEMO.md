# Demo state pack (B-L1-141)

Two tours. The first runs today on this machine. The second is the one the boss wants, and every
line of it is marked with what stands between it and reality.

Rule for both: **the output shown is output that was measured or that is specified, and the pack
says which.** No line here has been invented to look like a boot.

---

# Tour A — what runs right now

No toolchain, no kernel. What exists is 95 Goose files and seven auditors, and the auditors are
the only part of this layer that can be demonstrated without hardware.

```console
$ cd meta-os
$ python3 os-build/layer1/source_audit.py
...
95 files audited, 0 finding(s)
$ echo $?
0
```

What it proves: balanced braces, every called function defined in the file or an imported module,
every `E_*` declared in the registry, no double `let`, no keyword Goose does not have. What it
does **not** prove: that it compiles.

```console
$ python3 os-build/layer1/error_audit.py --unused
error registry audit
  declared: 34   used: 34   files: 95
...
$ echo $?
0
```

```console
$ python3 os-build/layer1/bootorder_check.py
boot order data test
  parsed: 22 rows, 22 names, bo_count() = 22

RESULT: boot order is consistent -- 22 services, dependency order proven, no cycles
NOT PROVEN: that the supervisor starts them in this order. That needs a boot log (B-L1-77).
$ echo $?
0
```

```console
$ python3 os-build/layer1/callmatrix_audit.py | tail -3
  watchdog     -> time         allowed, not called from a source

clean on permissions; 67 dormant row(s) reported above
$ echo $?
0
```

**This one was red when the tour was first written, and the fix is the interesting part.** Twelve
import edges had no permission and `fs`/`shell` had no id. They are in now (ids 22–24, twelve rows),
and so is a fix to the auditor itself: its `log`/`logd` alias was declared and never applied, which
had reported every edge to the log service twice. The 67 dormant rows stay on screen — they are
permissions that allow a call no import makes, and they are the next thing to drive down, not a
number to hide.

```console
$ python3 services/tests/hostile/hostile_check.py | tail -3
93 cases across 10 packs, 34 codes known
packs valid. NOTE: this proves the cases are well formed, NOT that any parser refuses them.
```

```console
$ python3 os-build/layer1/size_audit.py | head -4
size audit -- resident bytes for fixed arrays (slices are views, not storage)
  services: 27   resident: 393967 bytes (384.7 KiB)   unknown-element arrays: 0
```

Total: **7 of 7 gates green, 0 lines of this layer executed.** That sentence is the demo of today —
the gates prove the text is consistent with itself, and nothing more.

---

# Tour B — the shell session, when K6 lands

This is the walkthrough the boss asked for. Each block is the command, then the expected output,
then what has to exist for it to be true. Expected output is written from the service contracts,
not from a run.

## B1. Boot to a prompt

```console
$ goose run services/session/session.goose
[    0.000] bootlog  INFO  boot start, 22 services
[     ⟨ms⟩] bootlog  INFO  devices: ⟨n⟩ devices, 1 display, 1 keyboard
[     ⟨ms⟩] bootlog  INFO  storage: ⟨n⟩ blocks, RAM backend
[     ⟨ms⟩] bootlog  INFO  callmatrix: 21 services
[     ⟨ms⟩] bootlog  INFO  logd: 64 slots, retention 10 KiB
[     ⟨ms⟩] bootlog  INFO  agenthost: 0 agents
meta-os 0.1  (K6)  ⟨n⟩ services degraded: socket
login:
```

Needs: K2 framebuffer, K3 timer, K6 IPC and scheduling, and a real boot. **NOT BUILT.** Numbers
that are facts in source are written as facts (22 services in the boot table, 21 service ids in
the matrix, 64 log slots at 10 KiB); numbers that depend on the machine are `⟨n⟩`, because a
demo that invents a block count is a demo that will be quoted.

The `services degraded` line is the point of the tour, not decoration: a boot that reports clean
when `socket` failed is a boot that lies. The format is Hana's `shell-formats.md`, which this
layer does not emit yet.

## B2. The filesystem, from the shell

```console
login: user
password: ****
$ ls /
boot/  dev/  etc/  home/  tmp/        ⟨directory set is a policy choice, not yet fixed⟩
$ echo hello > /tmp/x
$ cat /tmp/x
hello
$ stat /tmp/x
/tmp/x  size 6  blocks 1  mode rw-r--r--
```

Needs: `fs` over `storage` over a real block driver (B-L1-74). Today `storage` is a RAM array and
`fs` is written against it. **NOT BUILT** end to end; the parser and path code are WRITTEN.

## B3. The call matrix refusing a call

```console
$ shell --as agent:7 cat /etc/shadow
cat: permission denied: fs.read, agent 7 has no CAP_STORE_READ
```

Needs: `agenthost` capability check actually wired into `cm_allows`, which is one of the twelve
missing matrix edges. **NOT BUILT.** The refusal string is specified by the audit path
(`audit_write` with `AK_DENIED`), not yet printed by a shell.

## B4. A failure you can see

```console
$ services
callmatrix  RUNNING   1.4s
logd        RUNNING   1.4s
...
agenthost   STOPPED   exit 3, crashloop, giving up
AGENT LAYER DOWN
```

Needs: the supervisor's give-up path plus the agent line. The line exists as data
(`ah_down_line`, `agenthost.goose:240`); the call site does not exist, and the supervisor's
crash-loop report is a plan, not code (`FAILURE_TRACE.md` items 3 and 7). **NOT BUILT.**

## B5. Update, verified

```console
$ updater check
manifest  6 files, signed ed25519, key 5f3a...
verify    sha256 ok, all 6
delta     1 file changed, 1.2 KiB vs 4.0 KiB
apply     staged, rollback armed
```

Needs: a real signature implementation (the tree has the *interface*, `updater/signature.goose`),
a filesystem that persists, and a boot to update. **NOT BUILT.**

---

# What each tour is worth, in one line each

- Tour A: seven mechanical gates over 95 files, all seven green — and the newest green one is the
  permission table, which was red until its last twelve edges were written in. Nothing executed.
- Tour B: five moments, all specified, none reachable. Every block names the missing piece, so
  nobody has to ask "is this real" — the answer is in the block.
