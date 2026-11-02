# What the services layer needs from the kernel after the hackathon (BF5-10)

Planning only. Every item is something this layer already calls, already needs, or already fails
without — none of it implies new feature work in the services. Ordered by what unblocks the most
with the least kernel change.

## 1. One image the kernel can map and jump to (blocks everything)

**Need:** a flat static image from a Goose program, a fixed load address, and a call into
`svc_entry` with the convention in `kernel/MAC_QUESTIONS.md` Q-B-L1-1.

**Who needs it:** all 25 services. Nothing in this layer can be started by a kernel until one image
exists, and the layer's runs today are host processes because of it.

**Cheapest proof:** `BOOT_PLAN.md` S1–S2 — the `svc bootlog: 0 <n> bytes` line. One service, one
image, one line.

## 2. `sys_ticks()` — proposal P1 (blocks 7 services)

**Need:** monotonic milliseconds since boot, number whatever the freeze rules (P1 asks for 6).

**Who needs it:** `bootlog`, `logd`, `time`, `console`, `display`, `shell`, `example`. Timestamps in
every log line and every supervisor decision are relative to it.

**Without it:** timestamps read 0, `time` fails its start check and returns 2, and the boot order
stops at service 3.

**Alternative if P1 is refused:** each service keeps a boot-relative counter from its own start. Ten
lines per service, and elapsed time across services becomes meaningless. The services side of that
change is mechanical; the ruling is not.

## 3. `sys_spawn`/`sys_kill` — proposal P3 (blocks the supervisor's whole purpose)

**Need:** start a service image and stop a process. `supervisor.goose` already documents the shape it
wants (`sys_spawn(image, len, priority) -> pid`, `sys_kill(pid) -> i32`) and deliberately does not
declare them until the signature is ruled.

**Who needs it:** `supervisor` — it decides correctly today (`t52`, `t75`: ten services, three
policies, a crash budget) and has no actor. Every other service needs it second-hand, because the
supervisor is what starts 7–22 in the boot order.

**Without it:** the layer stays a set of libraries plus a rehearsal. This is the line between "the
services work" and "the OS starts the services".

## 4. The start timeout (blocks the one failure class that is invisible)

**Need:** `starting_since_ms` on the supervisor slot, checked by its tick, so a service that never
reports ready is killed and recorded as failed.

**Why now, not later:** `console` hangs in the rehearsal today. On a kernel with a serial console
that hang is the boot, and nothing in this layer notices. The supervisor has the field in its design
and not in its table.

**Cost:** one field, one comparison in the tick path, one test that plants a service in STARTING.

## 5. `sys_read_key` returning a distinguishable "nothing yet" (already landed, needs a witness)

**Need:** nothing new — the call exists at number 5. What is missing is a kernel-side shell that
consumes it so this layer's `console` service can be exercised against a real keyboard instead of a
shim that always answers "nothing pending".

**Consequence today:** the shim's honest refusal is what makes `console` hang; on the kernel it would
block until a key arrives, which is correct behaviour and needs the start timeout above to be safe.

## 6. A place to put static storage (blocks the loader, quietly)

**Need:** a ruled per-process static storage size and a zeroing rule. Goose services never allocate;
their storage is a linker constant, and `ring`, `bootlog` and `audit` assume zeroed slots.

**Why it is listed separately:** it is not a syscall and it is not an image format — it is a number
and a yes/no, and without it the loader has nothing to size.

## 7. Block storage (blocks persistence, not the demo)

**Need:** a real block device behind `storage`'s `sys_*`-free backend. The service already has the
contract, the quota arithmetic, the seal and the volatility flag; a disk driver is the missing half.

**What it buys:** the filesystem survives a reboot, the audit trail persists, the updater's rollback
record means something. None of that is needed to demo a session; all of it is needed to call this an
OS.

## The order, as a table

| # | Kernel work | Unblocks | Proof line |
|---|---|---|---|
| 1 | one image + `svc_entry` convention | any service starting at all | `svc bootlog: 0 <n> bytes` |
| 2 | P1 `sys_ticks` | 7 services, timestamps | `svc time: started (order 3) ticks <n>` |
| 3 | P3 `sys_spawn`/`sys_kill` | supervisor acting on 25 | `svc supervisor: started (order 6) 22/22 running` |
| 4 | start timeout | hung-service detection | `svc console: starting, timed out after <n> ms` |
| 5 | static storage size + zeroing | the loader sizing | `K6 load: image <n> bytes at 0x…` |
| 6 | block driver | persistence | `svc storage: up, <n> blocks, durable` |

## What this page does not ask for

- No new services. The corpus is 25 and four placeholders are a delete-or-write ruling, not a build.
- No changes to the frozen syscall numbers this layer already uses: 0, 1, 4 and 5 are enough for 17
  of the 25.
- No scheduler features beyond what `sys_yield` already assumes.
