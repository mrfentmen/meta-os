# First minute walkthroughs (H4)

Branch: `hana/os-shell`. Drafted from `shell-spec.md` and
`shell-formats.md` (Section O OS-213, OS-214, OS-215).

## Marker rule

Every step carries exactly one marker, in those words:

- `[NOT BUILT]`: the step needs a running OS and does not exist
  yet. No boot log proves it.
- `[DOC]`: the step is reading this file itself. That is real:
  the file exists and you are reading it.

Anything in these walkthroughs that is not real yet is marked
NOT BUILT in the file, in those words (OS-215). There are no
unmarked steps, and no step pretends a booted OS exists.

## The user's first minute

Step 0: Read this walkthrough file before touching the machine. [DOC]
Step 1: Power on the machine and watch the console. [NOT BUILT]
Step 2: The serial line `META OS KERNEL - alive (K1)` appears. [NOT BUILT]
Step 3: The framebuffer console draws the banner: `META OS`, milestone, memory, tasks as measured. [NOT BUILT]
Step 4: The prompt `metaos> ` appears and waits for input. [NOT BUILT]
Step 5: Type `help` and read the real command list, which today would be `commands: (none yet)`. [NOT BUILT]
Step 6: Type `status` and read the tasks, ticks, and heap lines that are measurable. [NOT BUILT]
Step 7: Type an unknown word and read `unknown command: <first-token>`. [NOT BUILT]
Step 8: The first minute ends at the prompt, the OS idle, no fake screen shown. [NOT BUILT]

Note on Step 2: the K1 source that prints the alive line is
WRITTEN in `kernel/src/main.rs`, but it is UNCOMPILED and
UNPROVEN — no QEMU boot log has been seen. So even Step 2,
the earliest boot step, is NOT BUILT until that log exists.

## The agent's first minute

Step 0: Read this walkthrough file and `shell-formats.md` for the record schema. [DOC]
Step 1: Open the serial port (COM1, 38400 baud, 8N1) and wait for the alive line. [NOT BUILT]
Step 2: Read the boot JSON record and check `os`, `milestone`, and `status`. [NOT BUILT]
Step 3: Request the status record and parse `tasks`, `ticks`, and heap fields, treating unmeasured fields as `null`, never as zero. [NOT BUILT]
Step 4: Compare the record facts to the console banner facts; they must match, because both come from the same source. [NOT BUILT]
Step 5: List the shell's real commands from the help output, which today would be none. [NOT BUILT]
Step 6: The first minute ends with the agent holding a parsed record of a live OS, not a scrape of console text. [NOT BUILT]

## What is real here

Only the documents are real: this file, `shell-spec.md`, and
`shell-formats.md` exist and can be read. Everything that
needs a booted kernel, a console, a prompt, or a status
answer is NOT BUILT. When a milestone lands with a boot log,
its steps move from NOT BUILT to proven, one step at a time,
with the log named — never in bulk, never on a promise.
