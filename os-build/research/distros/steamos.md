# SteamOS — the appliance that boots straight into the thing

Lane: Buffy, research and tools. Task B2 (Section H mirror, OS-108).
Written 2026-11-01. RESEARCH, nothing built or tested.

## What it is

Valve's Arch based distribution for the Steam Deck and living room machines.
It boots into a games session, not a desktop, and the desktop is a mode you
switch into. The interesting engineering is not the games: it is the read only,
atomically updated appliance model.

## The model, mechanically

- **Read only root filesystem.** The system image is not edited at runtime, so
  there is nothing for an update or a user to corrupt in place.
- **A/B image updates.** An update is written to the inactive slot and takes
  effect on reboot; the previous image remains as the fallback.
- **One primary session.** `gamescope` starts as the session. The desktop is a
  secondary mode, entered deliberately.
- **Apps outside the image** arrive as Flatpaks, so they do not need the image
  to change.
- Each image version is a named, dated artifact, and rolling back is choosing
  the other slot.

## What it does better

1. **The device does one thing when it turns on.** No launcher, no desktop, no
   decisions. The user is in the task within seconds.
2. **Updates cannot brick the machine**, because they never touch the running
   image.
3. **The signed image is the unit of trust.** If the image boots, the system is
   what it says it is.
4. **Apps and system are cleanly separated** by the Flatpak boundary, so user
   software cannot destabilize the OS.

## What it costs

1. **The read only root makes some legitimate work painful.** A read only root
   is hostile to a developer machine, and this project is a developer machine
   first.
2. **A/B doubles the image footprint** and requires a bootloader that can pick
   a slot.
3. **Appliance focus is a limit.** Anything outside the one job is second class
   by construction.
4. **Valve's stack is deeply tied to Steam** and the storefront, which is
   irrelevant to us and not separable in places.

## One borrowable idea

**Boot straight into the one surface the machine exists for.**

For a user first OS that is the console. For this OS specifically, the boss's
own framing is that agents are first class citizens, so the honest version is:
Meta OS boots into the **agent's structured view and the user's console at the
same time**, and neither is a mode you switch away from to get the other. Hana
owns the surface design (H1, `os-build/shell-spec.md`); the borrowable part
here is the *aggression* of the default. No splash, no chooser, no login
decision, one screen that is already the work.

The A/B half is the other idea, and OS-114 owns the full design note. SteamOS
is the strongest evidence that A/B is not exotic: a consumer device ships it to
millions of people who never learn the word.

## License position

- **The ideas (immutable root, A/B, single boot session, app/system split):**
  free to take. A/B updating is older than SteamOS; the *design note* we write
  is ours.
- **SteamOS itself is Arch based, so its userland carries the usual GPL:**
  GPL-2.0 in the kernel and much of userland. **License contaminated by
  default. Idea fine, code never.**
- **`gamescope` : MIT.** The one permissively licensed piece of the story, and
  the one we have no use for.
- **Steam client: proprietary.** Not a toolchain component, and not something
  to model our OS on.
- **Verdict: ideas only, and only the boot model and A/B.**

## Verdict for Meta OS

Take the aggressive default session and hand the A/B design to OS-114. Do not
take the immutable root as a rule for the carrier: the crew needs to edit
things, and we are not shipping a console.
