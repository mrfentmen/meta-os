# Rowan tasks — Round 4 (the 72-hour window)

From Pax, 2026-11-01 ~20:30 EST. Boss order: 72-hour all-in
window, everything substantive in the next 24 hours. Your 12-hour
lane (R-1 to R-8 in os-build/PAX_12H.md) stands and is the base of
this set. Branch: `rowan/kernel`. You are the only writer in
`kernel/src` tonight — one owner per file is a freeze rule, and
the kernel files are yours. Report on the branch; Milo gates,
Pax merges.

## RW4-1 — Finish R-1 to R-8 (from the 12-hour plan)

Banner tells the truth (`META OS 0.1`, milestone = last proven),
prompt + backspace + shift in the console, per-keystroke scancode
debug line gone, `uptime` print only as a command, `mem`, `ps`,
and syscall 5 `read_key` (F1: ruled, yours to implement in
`user.rs`). Proof per item: a boot log line, named in your report.
No framebuffer, no bootloader change, no `gdt.rs`/`traps.rs`
changes without telling Pax first.

## RW4-2 — Complete the shell command surface

Implement the full command set from Hana's `os-build/shell-spec.md`
when it lands (help, status, mem, ps, clear, uptime, plus the
unknown-command line in her exact wording). Until her spec lands,
finish RW4-1; do not invent strings she is freezing.

## RW4-3 — Put the syscall table in the spec

On your branch, propose the KERNEL_SPEC.md addition that records
the F1 freeze: numbers 0 exit, 1 write, 2 sleep, 3 pid, 4 yield,
5 read_key, 6-15 reserved, 99-class unknown refused; authoritative
implementation `kernel/src/user.rs`. Pax merges spec changes;
your job is the exact text.

## RW4-4 — Soak proof

One 10-minute QEMU run driven through `os-build/tools/drive.py`:
repeated help/status/mem/ps, the three userspace programs cycling,
crasher included. One log, committed, named in your report.
Pass = no panic, no hang, fault stays isolated to the crasher task.

## RW4-5 — The 2026-11-02 input

Keep `kernel/MAC_QUESTIONS.md` current, and add one short page:
your recommendation on `syscalls.rs` — wire it deliberately or
delete it, with the reason. The boss rules it tomorrow; your
recommendation is the input he reads. `syscalls.rs` itself stays
frozen and untouched tonight.

## Rules

Status words exactly PROVEN (named log) / WRITTEN / BLOCKED.
Every report states wired/dead line counts for the files you
touched. Hard freeze at H+9 of the 12-hour clock (05:12 EST)
applies to feature work; gate fixes only after.
