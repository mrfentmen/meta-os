# KERNEL BUILD-OUT SPEC (boss order, 2026-11-02)

What the kernel has, what it needs, and the standing order to
close the gap. Measured state (Pax census, 2026-11-02):
kernel/src = 5,731 lines across 13 files; the proven claim is
the banner, ring 3, three userspace programs, fault isolation,
and a shell that reports real state.

## Standing order — gap-fill (boss, 2026-11-02)

Everyone building on this OS USES the OS and the programs,
reads the code, and implements what is obviously missing —
a button, a setting, an application, a refused case handled
badly — without asking and without filing a list of what is
missing. Just add it, checkpoint it, and let the merge speak.
The fences do not move: kernel/src is Rowan's write lane
(proposals on room 1), syscalls.rs stays FROZEN, dispatch
stays simulated-only, the parked lanes (demo voice, local
model pack) stay parked, merges go through Pax.

## K1. Graphics wired

framebuffer.rs (576 lines) exists and is unwired: bootloader
0.9.35 exposes no framebuffer, so the kernel draws text at
0xB8000 and nothing else. The route is Rowan's spike part 2
(the bootloader-upgrade evaluation). Build-out: the upgrade
or the alternative it names, the framebuffer initialised at
boot, and the ribbon drawn by the kernel — proven by a
screendump in a committed boot log, never by description.

## K2. Readkey finished

The keyboard path completes: typed input reaches the shell,
commands run as typed. The pack is staged
(rowan/kernel-readkey-merge @ 419c209); the gate is the Mac
gate.sh boot log (user readkey entry, 8 tasks, no panic,
two-reader proof). On a green log Pax merges the same run.

## K3. Memory grows up

Today: boot map parsed, bitmap frame allocator, 4-level page
tables per task, a 512K kernel heap — and a fault kills the
task, cleanly, every time. To build, in order:
- Demand paging: a fault on an unmapped-but-promised page
  maps it and retries the task instead of killing it.
- Copy-on-write: shared pages copied on first write, so
  tasks can start from a common image cheaply.
- Swap: cold pages written out (rides K5's storage) and
  faulted back.
Each step proven the same way the isolation claim was: a
boot log where the new behaviour is the thing that happens.

## K4. Tasks can talk (IPC)

No channel exists between tasks today. Design from what the
kernel already has (task ids, the scheduler's queues): a
minimal message pass — send to a task id, receive with a
bound, a full box refuses rather than blocks forever.
Buffy's talker/listener userspace pair is the acceptance
test: if the pair cannot run, the design is wrong, not the
pair. Rowan writes the kernel side; the finding trail lives
on room 1.

## K5. Storage and a filesystem

No disk driver, no filesystem: programs arrive with the boot
image and nothing persists. Build: a block device over the
emulator's disk, then a simple filesystem — files named,
read, written, listed — proven by a boot that writes a file,
reboots, and reads it back. The shell gains the commands
only when the proof exists (help line changes are Pax calls,
as always).

## K6. Drivers beyond keyboard and text

In order of what the systems need: a serial line (the boot
log's second home and the debug channel), a timer source
finer than the scheduler tick, and network (the carrier has
it today; the bare-metal kernel does not). Each driver lands
with the boot log that shows it answering.

## K7. The long tail, found by using it

Under the gap-fill order, kernel-adjacent absences get closed
as they are found: exit codes the shell reports truthfully,
ps showing real states, the fetch screen's numbers drawn from
the same code the shell prints. If it is obviously missing
and small, it is built, not listed.
