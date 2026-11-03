# OC3B-202/203/206/207/208/209 — .desktop files + validation evidence

Home of this lane's entries: `os-build/logs/oc3b-desktop/` (8 files,
this branch). OC2's six entries are NOT duplicated here — referenced
from `agent-layer/desktop-entries/` @landwalls (see OC3B-desktop-inventory.md).

Validator: no `desktop-file-validate` on this Mac, so validation is a
pinned Python parse + field audit whose full output is committed as
`os-build/logs/OC3B-desktop-test.txt` (OC3B-210 proof). Linux lane
re-runs the real validator at image build; same assertions.

Results (from the committed test output):
- OC3B-203 validated: 8/8 parse as INI with a `[Desktop Entry]` group.
- OC3B-206 TryExec guards: 8/8 present, matching the Exec binary.
- OC3B-207 no terminal: 8/8 `Terminal=false`.
- OC3B-208 categories sane: all `;`-terminated freedesktop categories
  (System/Utility/AudioVideo/Settings/Player/Mixer/Calculator/Monitor
  + GTK;). No made-up categories.
- OC3B-209 OnlyShowIn: 8/8 `OnlyShowIn=XFCE;`.
- OC3B-204 Exec-on-image: DEFERRED to OC1 boot check — no squashfs
  tooling on this Mac to read the rootfs. TryExec on every entry is
  the stated guard; entries whose binary is absent hide themselves
  instead of erroring.
- OC3B-205 icon resolves: DEFERRED to OC1 boot check — icon names are
  the upstream package defaults (CODE-INSPECTED, not verified).
