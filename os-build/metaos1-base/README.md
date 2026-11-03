# MetaOS 1.0 — base + first boot (Hana lane, slice 1)

Source of truth: `os-build/METAOS_1.0_12H_PLAN.md` (main @80a7886c)
and `os-build/METAOS_1.0_RELEASE_CHECKLIST.md` (H+2: Cubic base project
committed — package list, accounts, first-boot setup, default
files/associations).

## What this slice is

- A Cubic project definition for an Xubuntu-core remaster (see
  `cubic-spec.md`). Cubic itself runs on the cut machine, not here.
- A package list (`packages.txt`): what the base keeps, adds, and
  removes. Removals are NONE in slice 1 — nothing is cut blind.
- A first-boot setup (`firstboot/metaos1-firstboot.sh` + its systemd
  unit): idempotent, never prompts, never stores a credential, never
  contacts the network. It applies the base defaults for the
  already-created user and leaves a done-marker.
- Default file associations (`defaults/mimeapps.list`): plain text,
  images, and PDF only. The browser association is Bond's lane
  (Chromium + Meta start page) and is deliberately left unmapped here.
- A validator (`validate.py`, stdlib only) that checks the whole
  slice: package format and duplicates, shell syntax, every mapped
  desktop file covered by the package list, no credential-looking
  strings, no forbidden artwork terms, and no touch of the frozen
  `kernel/src/syscalls.rs`.

## What this slice is NOT — said plainly

- No ISO is built here. This sandbox has no Cubic, no VM, and no
  Xubuntu ISO, so no boot was run here.
- The H+2 acceptance — "base boots to login in under 60s in VM,
  first-boot creates the user and lands on the desktop" — is UNPROVEN
  until a VM boot on the cut machine, with screendumps committed.
  This slice is CODE-INSPECTED level, not VERIFIED boot.
- Brand kit (name, logo, hex, wallpaper, password policy) is OC1's
  H+0 lane. This slice uses Xubuntu defaults until the kit lands and
  says so; it invents no logo, no hex, and no wallpaper.
- Accounts: the installer creates the user account (Calamares is
  Buffy's lane). This slice does not create users, set passwords, or
  ship any credential. The first-boot script only applies defaults
  for the account that already exists.

## Slice 2 — base flow wiring (dexubuntu step 3)

Pax's room-1 order 2026-11-02 ~23:52 EST: wire dexubuntu as step 3
of the base flow, after the packages and the OC1 theme apply, and
prep the H+4 base/firstboot evidence. This slice does that wiring
and nothing else. It edits no file from another lane: the theme
script stays OC1's, the dexubuntu scripts stay Pax's gap-fill, and
both are only referenced here, in order, in `cubic-spec.md`.

The wired flow, in order: `packages.txt` → `metaos-theme/apply.sh`
→ `dexubuntu/apply-in-chroot.sh` → `dexubuntu/verify-rootfs.sh`
as the identity gate (7/7 must PASS before ISO generation) →
first-boot install → defaults install → ISO generation with the
verify result in the cut record. The validator now checks this
wiring: the spec names the three steps in that order, the gate is
named, and both dexubuntu scripts pass `sh -n`.

Still NOT proven here, said plainly: no ISO is built in this
sandbox, no boot is run here, and dexubuntu on a real layered
image is still unproven — Milo's dexubuntu audit records the
verify logic as spot-checked on a planted rootfs only, with
real-image execution BLOCKED on the merge-layers pre-step (still
unimplemented as code) and no base ISO on this host. Pax's chroot
cycle (apply exit 0, 7/7 after, second apply exit 0) is Pax's
record, not re-run here. The H+4 evidence prep lives in
`hplus4-evidence-prep.md`: a checklist of what the cut machine
must capture, all of it still uncaptured from this sandbox.

## Fences (plan, absolute)

- Original assets only. Nothing from another vendor's artwork, icons,
  layouts pixel-for-pixel, or fonts ships in this slice.
- No mock or placeholder presented as done. Every claim above is
  labelled with what backs it.
- Simulated loopback dispatch only; never a real emergency service.
  This slice touches no dispatch path at all.
- `kernel/src/syscalls.rs` is FROZEN. This slice does not touch it.
- All merges through Pax. Nobody pushes main, nobody posts except Pax.
  This branch is Hana's own; it enters a cut only when Pax merges it
  and Milo signs the audit row.

## How Pax cuts ISO cut 1 from this

1. Merge this branch (after Milo's gate).
2. On the cut machine, open the Cubic project per `cubic-spec.md`,
   record the exact source ISO filename + SHA-256 in the cut record.
3. Apply `packages.txt`, install the first-boot unit + script and
   `defaults/mimeapps.list` into the remaster.
4. Build, boot in VM, time login, commit the screendump set.
5. If boot-to-login is 60s or over, or first-boot fails, that is a
   named H+2 failure — not a quiet pass.

## How Pax cuts ISO cut 2 from this (H+4)

Same flow as cut 1, plus the wired steps: theme apply, then
dexubuntu apply, then the verify-rootfs gate at 7/7, all before
ISO generation. The cut-2 record adds the verify result to the
cut-1 record items. H+4 proof is the login-to-desktop screenshot
set per `hplus4-evidence-prep.md`, captured on the cut machine —
not claimed from this sandbox.

## Run the validator

```
python3 os-build/metaos1-base/validate.py
```

Exit 0 means the slice is internally consistent. It does not mean
the ISO boots — see above.
