# OS-tonight scout — Rowan's machine (handoff to Pax, OS-006/OS-007)

Scouted 2026-10-26 ~17:05 ET at Del's order ("get the OS on a system by
tonight"). This is a handoff note, not an image-lane claim: the image
pipeline is Pax's lane. Facts below were measured on Rowan's VM, not
guessed. Status: **CODE-INSPECTED** (checks run, listed).

## Repo state at scout time

- `mrfentmen/meta-os` main: `acb855a`. Crew is live: Hana's briefing
  tasks (BRF-006…BRF-023) and the `intel/` package are on main.
- **No `os/` tree exists yet** (OS-006 is the next image-lane land).

## Rowan's VM as a build/boot host — measured

| Check | Result |
|---|---|
| `packer` | NOT installed |
| `qemu-system-x86_64` / `qemu-img` | NOT installed |
| `/dev/kvm` | ABSENT — no hardware acceleration |
| CPUs | 2 |
| RAM | 7 GB |
| Free disk (`~/workspace`) | 94 GB |
| Debian cdimage reachability | `https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/SHA256SUMS` → HTTP 200 |

**Reading:** this VM cannot run the Packer+QEMU primary pipeline
(OS-007) tonight as-is — no QEMU, and without KVM any boot would be
full emulation on 2 cores (a boot proof in minutes-to-tens-of-minutes,
not the 90-second budget). Disk and network are fine. If Del wants a
tonight boot proof on iron he controls, the honest candidates are the
demo laptop (the named demo hardware, OS-002) or a VM on Del's PC —
both are Pax/Del-side calls, not Rowan's.

## What Rowan's lane already guarantees for tonight

- The kiosk payload exists and is local-file based: `bus.html` /
  `index.html` (byte-identical on main) plus `crew-board.html` — the
  OS-044 local-viewer rule can be satisfied the moment an image boots:
  dashboard renders from the image's own files, network unplugged.
- DSH-002's intel panel skeleton is in those files now, so a booted
  image tonight already shows the four mission-control panels.
- Rowan's boot-experience tasks (OS-042/043/045) are spec'd in
  `plan/META_OS.md` + the boot checklist and start the moment a test
  image exists to boot.

## Ask of the image lane (Pax)

When OS-006/OS-007 land, drop the image (or its build command) in the
repo or on the bus and Rowan will run the boot-checklist items that
touch the dashboard (checklist items 1, 4, 10, 12) on whatever target
Del names, and report results per item with evidence.
