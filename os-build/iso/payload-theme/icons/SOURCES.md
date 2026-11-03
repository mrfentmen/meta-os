# metaos icon set — provenance

20 files, all 128x128 RGBA, transparent, three blue tones only
(`(0,0,170)` fill, `#1877F2` edge, `(85,85,255)` highlight — verified by the
palette audit in the D identity report).

## Vendored (16) — from the live image, byte-identical

Extracted from `/usr/share/icons/metaos/` on `/tmp/metaos.ext4` (installed
2026-11-03 by the image build; generator uncommitted on this branch, so the
installed bytes are the source of truth). Per-file sha256 in
`SOURCES.sha256`; `theme_proof.sh` re-hashes repo vs image.

about aegis board calculator calendar dashboard files imperium musica
nervus notes officina science settings terminal trash

## Drawn (4) — generate-icons.py, this lane

The 17-dock set needs four names the vendored set lacks:

| file | glyph | dock app |
|---|---|---|
| `web.png` | ring + horizon bar | Web |
| `editor.png` | angle brackets + slash | Code Editor |
| `agents.png` | ring + dot (echoes `face/plymouth/ring-dot.png`) | Agents |
| `custos.png` | shield + spine | Custos |

## Drawn (6) — generate-icons.py, agent-1 (second batch)

The 27-dock set needs six more names; `about.png`/`aegis.png` already exist
and are reused, not redrawn:

| file | glyph | dock app | distinct from |
|---|---|---|---|
| `boards.png` | 2x2 solid blocks, one LITE | Boards | `dashboard.png` (thin 3x3 line grid) |
| `messages.png` | speech bubble + text bars | Messages | `agents.png` (ring + dot, no tail/bars) |
| `logo.png` | canvas frame + M-stroke | Logo Studio | `board.png` (pencil), `notes.png` (page + pencil) |
| `music3d.png` | quaver + LITE depth ghost | Music 3D | `musica.png` (single quaver) |
| `notes3d.png` | two stacked pages, no pencil | 3D Notes | `notes.png`, `music3d.png` |
| `budget.png` | ascending bars on an axis | Agent Budget | nothing else (only chart) |

Regenerate: `python3 generate-icons.py` (Pillow only, no external art).

## Papirus recolor (not binaries — build-host step)

Folder/mime icons come from the upstream Papirus recolor documented in
`ICONS.md` (`recolor-papirus.sh`, 78 `folder-blue*`/`user-blue-*` names).
This theme does NOT vendor Papirus: `index.theme` inherits it
(`Inherits=Papirus,elementary-xfce,hicolor`), and `check-icons.sh` resolves
inherited names against the target root so a miss fails loudly.
