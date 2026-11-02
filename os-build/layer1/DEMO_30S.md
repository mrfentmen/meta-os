# The services segment — 30 seconds (BF5-11)

For Hana's `DEMO_SCRIPT`. Only commands that ran natively in this checkout appear here; every line on
screen comes from `captures/demo-3-shell-session.txt`, and every number is in `DEMO_FACTS.md`.

## The timed script

| Time | On screen | Said |
|---|---|---|
| 0:00–0:05 | terminal at `meta>` | "This is the services layer: twenty-five services, no heap, no threads, no libc — written in a language called Goose." |
| 0:05–0:10 | type `help` | "The shell talks to the real filesystem service, not a mock. `help` lists what exists — and what deliberately does not." |
| 0:10–0:15 | `ls`, then `cat /etc/hostname` → `meta-os` | "A real file, read through the filesystem service: superblock, inodes, a directory, a block." |
| 0:15–0:20 | `ps` → three services with `stopped  restarts=0` | "The supervisor's table. Every service is registered, has a state and a restart count." |
| 0:20–0:25 | `cat nope`, then `ls \| grep x` | "Refusals matter more than features: a missing file is an error, and a pipe is refused instead of quietly becoming a filename." |
| 0:25–0:30 | cut to `captures/demo-1-supervisor-under-load.txt`, first 10 lines | "Ten services, three restart policies, a crash budget — decided by the supervisor, proven by a run, and not yet started by a kernel." |

## The exact lines that must be on screen

From the capture (`demo-3-shell-session.txt`), in order:

```text
meta> help
commands: help echo pwd cd ls cat cp rm mkdir ps uptime log audit time exit
no pipes, no redirection, no globs, no variables
meta> ls
etc/
motd
meta> cat /etc/hostname
meta-os
meta> ps
logd  stopped  restarts=0
net  stopped  restarts=0
supervisor  stopped  restarts=0
meta> cat nope
cat: nope: not found
```

If a line on screen is not in that file, it is not in the demo.

## What not to say in these thirty seconds

- **"The OS is running these services."** It is not: these are host processes against a substituted
  syscall surface. Say "the services layer, running on this machine".
- **"The kernel starts them."** Nothing starts them. Three start when called directly, in the
  rehearsal, and `BOOT_REHEARSAL.md` is the honest reference.
- **"It persists."** Storage is RAM. A reboot starts from zero.
- **Any number not in `DEMO_FACTS.md`.** If it is not generated from a command, it is a guess with a
  microphone.

## Fallback if the terminal misbehaves

Two static captures are demo-grade on their own, both regenerable:

```sh
./os-build/layer1/run_native.sh t76_demo_session t75_supervisor_load
cp os-build/layer1/host/build/t76_demo_session.log os-build/layer1/captures/demo-3-shell-session.txt
```

`captures/demo-2-filesystem.txt` (the filesystem's 75 checks) is the third, and it is the one to show
if someone asks "how do you know the filesystem works" rather than "show me the shell".
