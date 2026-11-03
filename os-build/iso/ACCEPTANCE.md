# Acceptance evidence — boot + installer lane

Maps this lane's two checklist boxes in
`os-build/METAOS_1.0_RELEASE_CHECKLIST.md` to the exact commands that
produce their evidence, and gives Pax the label text to paste. Nothing here
is evidence by itself; the files named below are.

Clock reference: H+0 = 2026-11-02 21:46 EST, H+12 = 2026-11-03 09:46 EST.

## H+2 — "Plymouth splash in the base (Buffy)"

Requires Hana's Cubic base (or a base ISO) first. Two modes, same payload.

```sh
# Cubic chroot route
sudo os-build/iso/build_iso.sh --root <h Cubic custom-root>
# then Generate in Cubic; ISO lands wherever Cubic writes it

# Or patch a base ISO (Linux + root)
sudo os-build/iso/build_iso.sh --iso <base.iso> --out metaos-1.0-amd64.iso
```

Evidence to capture, in this order:

```sh
os-build/iso/tools/vm_install_proof.sh --iso metaos-1.0-amd64.iso
```

Produces `proof/<stamp>/01-splash.png` and `02-live-desktop.png` with
`INDEX.md` T+ stamps.

What the checklist box needs:

- splash frame showing the Meta mark (not the base flavour's splash)
- the time from harness start to the desktop/login frame, quoted as the
  `at` value from `INDEX.md`, **with the accelerator named** — TCG numbers
  are upper bounds, KVM numbers are still virtual
- if the base autologins the live session, `02-live-desktop` is the
  "boots to desktop" frame; if it shows LightDM, that is the login frame.
  The difference must be stated, not glossed.

Paste-ready label: `CODE-INSPECTED + VM screendump set committed` only after
the frames exist. Before that: `BLOCKED — no Linux build host`.

## H+8 — "Calamares preseeded + clean install, reboots to login (Buffy)"

```sh
os-build/iso/build_iso.sh --inspect metaos-1.0-amd64.iso   # payload landed?
os-build/iso/tools/vm_install_proof.sh --iso metaos-1.0-amd64.iso \
     --keys ret,ret,ret,ret --reboot
```

Expected frame set:

| frame | what it proves |
|---|---|
| `01-splash` | Meta splash in the live boot |
| `02-live-desktop` | live session up |
| `03-installer-welcome` | Calamares launched, Meta branding, no dead links |
| `04-key-*` | each walkthrough step reached the next page |
| `05-installed-login` | installed disk boots to LightDM, no autologin |

The password is typed by the operator; Calamares 3.x has no unattended
mode. If the walkthrough needed more than the fixed key list, attach with
`--vnc 127.0.0.1:7`, complete it by hand, and say so — a hand-driven
install with screendumps is still a clean install; a claimed automated one
is not.

Paste-ready label: `VERIFIED (frames read by Pax)` only when Pax has opened
`INDEX.md` and every frame above exists. Otherwise `UNIMPLEMENTED —
install not run` (never `done`).

## What is already true, without a Linux host

- `test/run_checks.sh` — the lane gate: validator, shell syntax, base-hash
  fixture and a real QEMU dry frame in one command (9 checks).
- `tools/check_configs.py` — 42 assertions, 0 fail, 0 skip: YAML parses,
  module refs complete, exec-order chains, preseed values asserted, no
  base-flavour strings in shipped values, assets hashed, no shipped font or
  Apple-adjacent value, 12-dot splash ring intact.
- `test/verify-base.test.sh` — the base-ISO hash gate refuses a tampered or
  unsummed image; opt-out is explicit.
- `tools/vm_install_proof.sh --dry` — real QEMU framebuffer capture; proves
  the harness, nothing about MetaOS.

Those two are the only claims this lane can make on the Mac. Everything
else waits for the build host.
