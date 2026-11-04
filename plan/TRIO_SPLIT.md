# Trio split: one console became three apps

Written 2026-11-04. What changed, where it lives, how to prove it.

## The problem

Two dock tiles, `Trio` and `Imperium`, opened the same page. Trio was supposed
to be the police, fire and EMS product, but it opened the logo studio for weeks
and then Imperium's console. A judge clicking both tiles saw one screen twice,
which is the fastest way to lose a demo.

## What replaced it

Three separate apps on one backend:

| App | Page | Layout | Accent |
| --- | --- | --- | --- |
| Vigiles (police) | `trio/vigiles.html` | map fills the frame, camera list in a left rail, three counts in a status strip | cold blue |
| Ignis (fire) | `trio/ignis.html` | 2x2 live video wall, captions under each stream, timeline down the left | amber |
| Medicus (EMS) | `trio/medicus.html` | three triage columns (Immediate / Delayed / Unseen), search in the header, crew strip at the bottom | green |

Imperium stays as the cross-division command console. The old `Trio` tile is
gone because it duplicated Imperium; the four tiles now open four different
screens.

Shared code sits in `trio/core.js`: camera list and the `/api/cameras` fetch,
the watch list, `assess()`, the agent crew status, the local map projection,
and the store. Each page imports it and renders its own way. Nothing about the
backend changed.

## Wiring

- `os-build/iso/payload-theme/apps/metaos-imperium.py` takes
  `--division vigiles|ignis|medicus`. Unknown names exit 2 with the list. The
  page is served over `http://127.0.0.1:8080/trio/<page>` from the site root,
  because the pages are ES modules and `file://` blocks the import.
- `os-build/face/meta-desktop.sh` writes four tiles:
  `Imperium`, `Vigiles`, `Ignis`, `Medicus`, with icons `imperium`, `police`,
  `fire`, `ems`.
- `os-build/face/metaos-update.sh` copies `trio/` to `/opt/face-site/trio/`.
- The icons come from `os-build/iso/payload-theme/icons/app-icons.py` and are
  written into `icons/metaos/` by
  `gen-icon-accents.py --sync-default`.

## Proof that exists

Rendered headless at 1440x900 against the live backend on 127.0.0.1:8080,
with real NYCTMC cameras loaded (975 online):

- `os-build/captures/trio-vigiles-20261104.png` — 975 dots on the map, camera
  rail populated, counts in the strip.
- `os-build/captures/trio-ignis-20261104.png` — four live streams, per-tile
  Watch/Assess, session timeline.
- `os-build/captures/trio-medicus-20261104.png` — three empty triage columns,
  crew strip reading `no crew records yet`, board `0 / 6`.

Launcher check: `--division bogus` prints
`unknown division 'bogus' (have: ignis, medicus, vigiles)` and exits 2.
`--division vigiles` gets past the page lookup and stops at
`GTK/WebKit unavailable` on this Mac, which is the expected failure off-image.

Not proven: nothing has been installed into `/tmp/metaos.ext4` yet, and no
boot happened for this change. The images above come from the host, not the
guest.

## Deploying

```
sh os-build/tools/sync_image.sh            # copies the tree in, provisions
```

Then the four tiles appear on the next login. If a tile still opens the old
page, the image is stale: `metaos-update.sh` pulls `main`, and this work lives
on the current branch until merged.
