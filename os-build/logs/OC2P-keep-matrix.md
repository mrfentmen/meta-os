# OC2P evince-vs-atril KEEP matrix (read-only, Hana decides)

| File | Says |
|---|---|
| `os-build/metaos1-base/packages.txt:13,21` | KEEP comment + list: `evince` |
| `os-build/metaos1-base/defaults/mimeapps.list:8` (canonical) | `application/pdf=evince.desktop` |
| `agent-layer/desktop-entries/mimeapps.list` (drop-in) | `application/pdf=atril.desktop` (comment: base ships atril) |
| `os-build/metaos1-base/validate.py:88` map | `evince.desktop → evince` (atril not in map) |
| `agent-layer/desktop-entries/evince.desktop` | degraded-off, `NoDisplay=true`, pending Hana ack |
| `agent-layer/desktop-entries/atril.desktop` | active; notes KEEP still says evince |
| `os-build/OPENCODE2_500_STATUS.md` proposal | STATUS proposal only, Hana files untouched |

Hana decision needed (one line in the cut record): whether the source ISO
carries `evince` per KEEP or the KEEP line should read `atril`. Until then
OC2 ships both and maps PDF to atril in the drop-in only.
