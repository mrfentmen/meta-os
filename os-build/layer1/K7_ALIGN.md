# The service shell against the kernel's K7 session, line by line (B3)

Two shells exist in this project and they are not the same program. This page puts the
kernel's own K7 session log (`os-build/logs/K7-boot.txt`, the newest one on `main`) beside
the native service-shell transcript (`host/build/t76_demo_session.log`, produced by
`services/tests/t76_demo_session.goose`), command by command, and says where they match.

The comparison is the point. A demo that says "the shell" while showing one and quoting the
other would be describing two things as one.

## The sessions

Kernel shell, from `K7-boot.txt` (serial output, after the user tasks exited):

```
help
commands: status help uptime mem ps
status
tasks 7 ticks 12587 heap_free 287K
STATUS tasks=7 ticks=12587 heap_free_kb=287
mem
mem frames_free 127150 frames_total 127199 heap_free 287K heap_total 512K
ps
ps id 1 state Exited ticks_used 0 prio 0
ps id 2 state Exited ticks_used 0 prio 0
...
uptime
uptime 141s ticks 14192
boguscmd
unknown command
commands: status help uptime mem ps
```

Service shell, from `t76_demo_session.log`:

```
meta> help
commands: help echo pwd cd ls cat cp rm mkdir ps uptime log audit time exit
no pipes, no redirection, no globs, no variables
meta> ps
logd  stopped  restarts=0
net  stopped  restarts=0
supervisor  stopped  restarts=0
meta> uptime
up 0s  lines=12  errors=0
meta> frobnicate
unknown command: frobnicate
```

## The alignment, one row per shared command

| Command | Kernel K7 says | Service shell says | Verdict |
|---|---|---|---|
| `help` | `commands: status help uptime mem ps` | `commands: help echo pwd cd ls cat cp rm mkdir ps uptime log audit time exit` | **SAME VERB, DIFFERENT LIST.** The kernel offers 5, the service offers 15, and each list contains names the other does not have. |
| `ps` | `ps id N state Exited ticks_used 0 prio 0` | `<service>  <state>  restarts=N` | **DIVERGES.** Both list what is running, from opposite ends: the kernel lists tasks with a pid and CPU time, the service lists supervised services with a restart count. No field is shared except the state word. |
| `uptime` | `uptime 141s ticks 14192` | `up 0s  lines=12  errors=0` | **DIVERGES.** The kernel reports seconds and its tick counter. The service reports seconds since its own clock started plus shell counters, because a tick count it cannot prove is not a number it will print. |
| unknown command | `unknown command` then the help list again | `unknown command: frobnicate` | **DIVERGES.** The service names the token that failed; the kernel reprints help instead. Both refuse — that part is aligned. |
| prompt | no prompt in the log | `meta> ` before every command | **DIVERGES.** Either the kernel prints none or the serial capture strips it; the log cannot tell us which, so this page does not claim one. |
| `status` | `STATUS tasks=7 ticks=12587 heap_free_kb=287` (machine line) + a human line | not implemented | **KERNEL ONLY.** |
| `mem` | `mem frames_free … heap_total 512K` | not implemented | **KERNEL ONLY.** |
| `ls`, `cat`, `pwd`, `cd`, `echo`, `cp`, `rm`, `mkdir`, `log`, `audit`, `time`, `exit` | not implemented | implemented and exercised in this transcript | **SERVICE ONLY.** |

## What this alignment proves, and what it does not

**Proven:** four command names are shared (`help`, `ps`, `uptime`, and the refusal path),
and **not one output line is identical between the two shells.** The service shell does
strictly more (filesystem and log commands) and strictly less (`status`, `mem`) than the
kernel shell.

**Not proven:** that they are the same binary, the same parser, or that either one will
survive being pointed at the other's world. They are two implementations in two languages
(Rust for the kernel, Goose for the service) that happen to agree on four words.

**The demo consequence, stated for `DEMO_30S.md` and Hana's script:** the 30-second segment
shows the **service** shell, so every line on screen comes from `t76_demo_session.log`, and
no line from `K7-boot.txt` may be shown as if the same session produced it. If the segment
needs `status` or `mem`, those come from the kernel boot log and are labelled as the kernel's.

## Reproduce

```
./os-build/layer1/run_native.sh t76_demo_session
sed -n '/^help$/,/^commands:/p' os-build/logs/K7-boot.txt     # kernel side, as recorded
sed -n '/meta> help/,/frobnicate/p' os-build/layer1/host/build/t76_demo_session.log
```

The kernel side cannot be reproduced on this machine — it is a boot log captured on the
director's Mac (`os-build/logs/`). This page quotes the file; it does not re-run it.
