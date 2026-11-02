# The demo shell session, and what it lines up with (BF5-05)

Hana's demo needs the services layer to say the same words the kernel shell says. This page is the
alignment, and it is deliberately half-red: the services side is measured, the kernel side is not in
this checkout.

- **The session itself** is `TRANSCRIPTS.md` § BF5-05 — `tests/t76_demo_session`, 25 checks, run
  2026-11-02, output unedited. Everything in it goes through the shell service against the real
  filesystem service.
- **The story** is `DEMO_FACTS.md`. If a number here disagrees with that file, that file wins.

## The commands the demo can actually speak

| Command | Ran in the session | What it shows |
|---|---|---|
| `help` | yes | the command list, and the sentence "no pipes, no redirection, no globs, no variables" |
| `pwd` | yes | `/`, then `/tmp` after `cd tmp` |
| `ls` | yes | `etc/` and `motd` — the trailing slash is how a directory is marked |
| `cat motd` | yes | `welcome to meta os` |
| `cat /etc/hostname` | yes | `meta-os`, an absolute path |
| `mkdir tmp`, `cd tmp`, `cd ..` | yes | the working directory follows |
| `echo meta os` | yes | arguments are literal; no expansion exists to surprise the audience |
| `ps` | yes | `logd  stopped  restarts=0` per registered service |
| `uptime`, `log`, `audit`, `time` | yes | the system builtins, against the supervisor and log tables |
| `cat nope` | **refused** | a missing file is an error, not silence |
| `ls \| grep x` | **refused** | scripts are one command per line; the shell says so instead of creating a file named `\|` |
| `frobnicate` | **refused** | the unknown-command path |

## The alignment with the kernel shell, cell by cell

The kernel's shell (Rowan's R-2..R-8 round) speaks `help`, `uptime`, `mem`, `ps`, and it has a
feedback loop for editing. The services shell speaks the list above. The overlap is `help`, `uptime`,
`ps`.

| Word | Kernel shell | Services shell | Aligned? |
|---|---|---|---|
| `help` | prints a command list including `uptime` | prints a command list including `exit` | **format differs** — both lists are hand-written strings in two places |
| `uptime` | prints the kernel's tick count as seconds | prints the supervisor's uptime line | **format differs** |
| `ps` | prints the kernel's process table | prints the supervisor's service table | **format differs**, and the columns are not the same facts |
| `mem` | kernel only | absent | kernel only, correctly |
| `ls`, `cat`, `cp`, `rm`, `mkdir`, `cd`, `pwd`, `echo` | absent | present | services only, correctly: the kernel has no filesystem |
| `log`, `audit`, `time` | absent | present | services only |

**Status: NOT ALIGNED, and the difference is not a bug — it is two shells.** One runs in the kernel
with no filesystem; one runs in userspace with the services. The alignment task (BF5-05's "line by
line with the kernel's K7 log") cannot be completed on this checkout because **there is no K7 log in
this tree**. What is missing to complete it:

1. the kernel's `help`/`uptime`/`ps` output, one capture each (Milo's or Rowan's gate file);
2. a ruled output shape for the three shared words — `os-build/shell-formats.md` (Hana) already
   specifies a `KEY value` shape, and `services/status` implements the services side of it;
3. one commit that changes the strings, when someone owns both files. Two writers to one format is
   how the drift started.

## What the demo should do with this

Say the services half and do not imply the kernel half:

> "This is the userspace shell driving the services layer on a real filesystem: `help`, `ls`, `cat`,
> `ps`, `uptime`, and the refusals. The kernel's shell speaks three of these words with its own
> formatting; unifying them is on the board for tomorrow, and the spec for it exists."

That sentence is true, checkable, and it does not depend on a log that is not in this tree.
