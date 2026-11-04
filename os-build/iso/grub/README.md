# Lane F — GRUB boot chain (OPENCODE R5, branch agent-r5)

Owned paths: `os-build/iso/grub/**`, `os-build/iso/kernel/**`. Read-only
elsewhere. Status words: DESIGNED / WRITTEN / COMPILED / VERIFIED / NOT BUILT / BLOCKED.

## F2. Second GRUB entry — `40_metaos.cfg` (WRITTEN, DISABLED)

Labelled `MetaOS kernel (experimental)`, clearly distinct from the default
entry (`Try or Install MetaOS`, owned by lane C via
`finalize-iso-tree.sh:13-16`). Default entry's label and index untouched:
this file only *appends* a new stanza; it renames, reorders, and edits nothing.

Default-untouched proof (re-run on this Mac, 2026-11-04):

- `grep -rn "GRUB_DEFAULT" os-build/iso/payload-theme/ os-build/identity/` → empty, rc=1.
- `grep -rn "set default\|set timeout\|GRUB_TIMEOUT" <this dir>` → empty by construction
  (no such line exists in `os-build/iso/grub/`; verify with
  `grep -rn "default\|timeout" os-build/iso/grub/40_metaos.cfg` — only the word
  "default" in comments).
- `finalize-iso-tree.sh` still performs only string replacement on the two
  stock stanzas plus layerfs/console flags; this lane did not edit that file
  (outside owned paths).

## F3. Tree-builder wiring — NOT wired, patch proposed (BLOCKED by ownership)

`build_iso.sh` and `merge-layers.sh` are outside owned paths, so this lane
does NOT edit them. `--tree-only` exit-0 therefore cannot be claimed by this
lane; record: NOT wired, by rule. Request for lane C (exact 5-line patch,
to run after the `finalize-iso-tree.sh` call in `merge-layers.sh:174-176`
and the equivalent `--iso` path in `build_iso.sh:349-357`):

```sh
# Lane F hook (applies ONLY when METAOS_KERNEL=1 in the environment):
[ "$METAOS_KERNEL" = "1" ] && [ -f "$SCRIPT_DIR/grub/40_metaos.cfg" ] \
  && cat "$SCRIPT_DIR/grub/40_metaos.cfg" >> "$WORK/iso/boot/grub/grub.cfg"
# Default (env unset): byte-identical grub.cfg to today. Default entry index 0.
```

Effect: default builds ship zero bytes of change; opt-in builds append the
experimental stanza. Guard variable defaults off.

## F4. Container gate — BLOCKED (Mac, by rule)

ISO builds run inside Linux containers only (`merge-layers.sh` needs
xorriso, unsquashfs, chroot; this Mac has none: `which xorriso unsquashfs`
both empty, `uname -s` = Darwin). No container build attempted on this Mac
per lane orders. The snippet that a container build would append is the file
itself — pasted verbatim from `40_metaos.cfg`, not from a container log:

```grub
if [ "$metaos_kernel" = "1" ]; then
menuentry "MetaOS kernel (experimental)" --class metaos {
    search --no-floppy --file /boot/metaos-kernel.img --set khd
    multiboot /boot/metaos-kernel.img
    boot
}
fi
```

Full text with per-line failure annotations: `40_metaos.cfg`.

## F5. QEMU boot of our entry — BLOCKED (no bootable ISO containing it)

There is no ISO carrying the experimental entry (F3 not wired, F4 blocked),
so there is nothing to select in QEMU. No serial log faked. What the proof
will look like once the lead wires it: `qemu-system-x86_64 -cdrom <iso>
-serial file:<log> -m 2048`, select `MetaOS kernel (experimental)`, capture
serial; PASS = `META OS KERNEL - alive (K1)` line in the log. Expected
today: FAIL at `search`/`multiboot` (see `../kernel/WHY_NOT_BOOTING.md`) —
which is why the entry stays disabled.

## F7. Default entry still boots — BLOCKED on this Mac (proof shape stated)

QEMU exists here (`/opt/homebrew/bin/qemu-system-x86_64`) but BOOT_POLICY
restricts boots to the high-RAM build Mac at milestones, one booter at a
time; no boot run by this lane. No screenshot faked. Proof shape when lane C
runs it: screenshot of the Meta-branded desktop session + serial/log showing
`autologin-user=meta, user-session=metaos`, ISO sha256 recorded alongside
(BOOT_POLICY: "or it didn't happen").

## F8. Boot time before/after — BLOCKED (same reason as F7)

No timing run without a boot. Regression rule stands: if the default entry's
time-to-session regresses after wiring, this lane fails. Rationale for
expecting none: unwired default builds are byte-identical (F3 patch is
env-gated), so the timer cannot move.

## F9. Meta-branded GRUB menu — config WRITTEN, render BLOCKED

Branding without behaviour change = the existing staged theme, owned by
lane C/G, which this lane re-states and does NOT alter:

- `payload-theme/grub/theme.txt`: `title-text: "Meta OS 1.0"`,
  `title-color "#EDF5FF"`, `desktop-color "#070B16"`, accent `#1877F2`,
  `timeout = 10`, `show_timeout = true`. Timeout 10 preserved exactly.
- No `GRUB_DEFAULT` / `GRUB_TIMEOUT` / `set default` / `set timeout` line in
  any owned path (grep proofs in F2). Default entry index 0, timeout
  behaviour unchanged by construction.
- Screenshot of the menu: BLOCKED (no rendered boot on this Mac; needs
  Linux+QEMU ISO boot, lane C's run). Render check when run: photograph the
  menu, confirm title reads `Meta OS 1.0`, countdown shows 10, first item is
  `Try or Install MetaOS`.

## F10. Stock splash/logo gone from the GRUB path — config diff WRITTEN, render BLOCKED

- `payload-theme/grub/` contains zero distro strings:
  `grep -rni "ubuntu\|xubuntu\|debian" os-build/iso/payload-theme/grub/` → empty, rc=1.
- `finalize-iso-tree.sh:13-16` rewrites every stock menu string the base
  GRUB ships (`Try or Install Xubuntu/Ubuntu` → `Try or Install MetaOS`,
  `Xubuntu/Ubuntu (safe graphics)` → `MetaOS (safe graphics)`); its 4
  `Xubuntu|Ubuntu` grep hits are the *patterns replaced*, not shipped text.
- This lane's `40_metaos.cfg` adds zero stock strings (entry class `metaos`,
  label `MetaOS kernel`).
- Pixel proof (menu screenshot + first second after it): BLOCKED, same run as
  F9. What it must show: Meta theme background + mark, no brown/orange stock
  artwork on either screen.

## F13. ISO path / size / sha256 + two boot outcomes

- Base: `/tmp/xubuntu-base.iso`, 5211408384 B,
  sha256 `4ed869ebf2b9f2f6118c1b60b9ed07576e8fe3d5cdfe10aae06869e669878b81`
  (`shasum -a 256`, 2026-11-04). Matches `LAYERS_TRUTH.md:A8` byte count.
- Built product ISO with this lane's change: DOES NOT EXIST (nothing wired,
  no container build). No path/size/sha to report; inventing one would be a
  fake. Reference only: `os-build/iso/output/metaos-1.0-arm64.iso`
  (2464088064 B, sha `d376f3d4…b5ca7` per its `.sha256` sidecar) predates
  this lane and carries none of it.
- Boot outcome 1 (default entry): NOT RUN — BLOCKED (F7).
- Boot outcome 2 (experimental entry): NOT RUN — BLOCKED (F5); expected FAIL
  per `../kernel/WHY_NOT_BOOTING.md`, hence disabled.

## F14. Our kernel is NOT default

Stated plainly: `40_metaos.cfg` appends after the default, never reorders
it; no `set default` / `GRUB_DEFAULT` anywhere in this lane. Making it
default is the lead's call after two consecutive green boots — not this lane,
not this round.

## F15. Handoff: boot-chain files still the distro's (for lane G)

Unchanged by this lane; the machine under the branding remains the base's:

1. `casper/vmlinuz` + `casper/initrd` (Ubuntu kernel + initramfs; rebuilt in
   chroot by `merge-layers.sh:149-167`, modules transplanted from the base's
   own `.live` layer, `:126-141`).
2. `boot/grub/grub.cfg` structure, El Torito BIOS+UEFI entries
   (`merge-layers.sh` GATE 5 replays them from the base), `layerfs-path` +
   `console=ttyS0` mechanics (`finalize-iso-tree.sh`, `grub-fix.sh`).
3. `casper/filesystem.squashfs` assembly + `install-sources.yaml` single-source
   rewrite (`merge-layers.sh:210-234`), casper UUID sync (GATE 6).
4. `etc/default/grub` (`GRUB_THEME` wiring = lane C; `GRUB_DISTRIBUTOR`/
   timeout values = base inheritance, lane G row 15 keeps hands off).
5. plymouth active theme selection at initramfs level (`provision.sh:186`
   rebuild; theme *content* is ours, the mechanism is the distro's).
6. All 1,876 base debs per `BASE_FACTS.md:41-53` (minus removals in
   `debrand2.sh`); kernel modules/firmware trees under `lib/modules`.
