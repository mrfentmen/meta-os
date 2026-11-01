# ChromeOS — a browser as the whole surface, and the update model underneath

Lane: Buffy, research and tools. Task B2 (Section H mirror, OS-109).
Written 2026-11-01. RESEARCH, nothing built or tested.

## What it is

An operating system whose user facing surface is a browser, running on top of
a hardened Linux, with a fully managed update model. The interesting half is
not the browser: it is verified boot plus A/B updates plus a stateless
userland, delivered to schoolchildren without a sysadmin.

## The model, mechanically

- **Verified boot.** Each boot stage verifies the next with a signature chained
  from read only firmware, so a modified system image refuses to boot rather
  than booting compromised.
- **A/B partitions with a mandatory update.** Updates download in the
  background, install to the inactive slot, and the device switches on reboot.
  If the new slot fails to boot, the device falls back.
- **Everything the user sees is the browser**, so the OS surface is one app
  that Chrome's own release cycle can update.
- **Stateless by default.** User data is in the cloud, so a "powerwash" is a
  supported, ordinary operation, not a disaster.
- **Linux and Android apps** arrive in containers as a deliberate second class
  citizen, not as part of the OS.

## What it does better

1. **Updates that are not events.** The user never plans one. This is the
   single biggest quality of life win of any OS on this list.
2. **Verification from firmware up**, so "did something modify my OS" has a
   real answer.
3. **A single surface means a single thing to make good.** No settings maze.
4. **Recovery is designed**, not improvised: the fallback slot is part of the
   boot contract.

## What it costs

1. **Everything not the browser is second class.** Local files, local tools,
   and development are all awkward by construction.
2. **It only works because of the cloud.** Statelessness is a feature for a
   school and a defect for a machine that holds an agent's memory (OS-120).
3. **The security model is a vendor relationship.** You are not the root of
   trust on your own device.
4. **Verified boot resists the user**, and this project's whole point is that
   the owner is in charge.

## One borrowable idea

**Recovery is part of the boot contract, not an emergency procedure.**

Both halves are worth stealing, and they are cheap at our scale. The goal for
our updater (OS-162, and OS-114's design note) should be stated as a contract:
an update writes the inactive slot, the active slot is never written, and a
slot that fails its own boot proof marks itself bad and hands back. Our boot
proof rule already gives us the primitive: a milestone is real when a log
shows it. Apply that to images, so a slot that cannot produce its log line is
automatically the rejected one.

For the agent side, verified boot has an analogue that matters more: an agent
should be able to verify *what it is running* before it acts on it, so an agent
home has a signed manifest of its tools and its own record chain (OS-124).

## License position

- **The ideas (verified boot, A/B, designed recovery, single surface):**
  free to take. All of them predate ChromeOS in some form.
- **Chromium OS: BSD-3-Clause.** Permissive, so the reference implementation is
  readable and borrowable in principle. We are not adopting it.
- **ChromeOS the product: proprietary.** Do not study the shipped product's
  internals as if they were a spec, and do not assume a behavior we see on a
  Chromebook is documented anywhere.
- **Verdict: ideas only.**

## Verdict for Meta OS

Take the update contract and the recovery-as-contract framing into OS-114 and
OS-162. Reject stateless userland outright: agent memory is state, and the
design should say so out loud before somebody "simplifies" it away.
