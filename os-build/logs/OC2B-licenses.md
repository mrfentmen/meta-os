# OC2B-015/016 — Python dependency licenses + redistribution verdict (ISO)

Scope: `server/queue/*.py`. Method: import scan (`OC2B-import-scan.txt`).

## Third-party Python deps found in imports

| Package | Imported in | License | ISO verdict |
|---|---|---|---|
| pillow (PIL) | `evidence.py` (`from PIL import Image`, lazy, crop path) | HPND (permissive) | PERMITTED — via `python3-pil` apt or `pip3 install pillow` |
| numpy | `evidence.py` (`import numpy`, lazy, cv2 path only) | BSD-3-Clause (permissive) | PERMITTED — via `python3-numpy` apt or `pip3 install numpy` |
| opencv (cv2) | `evidence.py` (lazy, `except → "unavailable"`) | VERIFY (opencv-python: Apache-2.0; Debian libopencv: BSD-3-Clause — confirm against pinned package) | VERIFY — and NOT REQUIRED: degrades honestly, install.sh deliberately omits it |

## Stdlib (no license action)

Everything else is stdlib (`argparse, base64, hashlib, http.server, json,
os, sqlite3, subprocess, sys, urllib.*, datetime...`). Zero third-party
requirement for queue/trio/patrol/crew/livecams/models/guardrail/store.

## Node sidecar (no npm packages)

`trio_repo.py` + `crew_common.py` shell out to system `node` to import the
repo's own `js/products.js` (no npm install, no third-party JS).
`trio_agent.py` validates via repo-own `js/schema.js`. Verdict: PERMITTED —
requires the `nodejs` package present (queue hard-requires node, no
fallback).

## Verdict (OC2B-016)

SHIPPED set = stdlib + pillow + numpy + system node. All permissive →
**redistribution on ISO permitted**. opencv explicitly NOT shipped; re-run
this verdict if it is ever added. Re-verify if any pin in
`OC2B-runtime-pins.txt` changes.

## OC2B-013/014 — permissions (intended; verified at commit)

Rule: units 644, scripts 755, env 600. No world-writable file ships.

- `~/.config/systemd/user/oc2-{queue,trio,patrol}.service,oc2-patrol.timer`:
  644, $USER (from `agent-layer/units/`).
- `~/.config/oc2-agent/env`: 600, $USER (installer refuses secret values).
- Entry points `server/queue/{queue_service,trio_agent,patrol,livecams}.py`:
  755 (bit SET this session — was 644; units call `/usr/bin/python3`
  explicitly so runtime never depended on it, but the contract now holds).
- Crew library `crew.py`, validators, models: 644 (library, no exec contract).
- ISO targets `/usr/share/metaos/*`: 644 files, root (OC1 packaging lane).
- `/var/lib/metaos/*` (PROPOSED): 644 files / 755 dirs.
