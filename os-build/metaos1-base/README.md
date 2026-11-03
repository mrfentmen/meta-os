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

## Run the validator

```
python3 os-build/metaos1-base/validate.py
```

Exit 0 means the slice is internally consistent. It does not mean
the ISO boots — see above.

## Slice 2 — first-boot dry-run test (own branch, after slice 1)

Slice 1 is left untouched as the gated item: this slice 2 lives on
branch `hana/metaos1-firstboot-test` and merges only after slice 1.

- The first-boot script accepts three test-only path overrides
  (`METAOS1_DONE_FILE`, `METAOS1_SYSTEM_DEFAULTS`,
  `METAOS1_HOME_ROOT`). The installed unit sets none of them, so
  installed behaviour is exactly the slice-1 defaults.
- `firstboot/test_firstboot.sh` runs the script against throwaway
  directories only and checks: a fresh user gets the system defaults,
  a second run leaves the user config alone, a pre-existing user
  config is never overwritten, and a run with no home directory
  still exits 0 and marks done.
- The validator runs this harness too, so `validate.py` exit 0 now
  covers the dry-run as well as the static checks.
- What this still does NOT prove: a VM boot, a login under 60s, or
  first-boot landing on the desktop. Those stay owed at Pax's
  ISO cut 1, with screendumps, and are Milo's gate — not claimed
  here.

```
sh os-build/metaos1-base/firstboot/test_firstboot.sh
```
