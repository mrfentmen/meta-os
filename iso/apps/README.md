# MetaOS core apps (Bond lane, H+6)

Launch configs only — no app is rewritten, no stub ships. Xubuntu already
has `thunar`, `xfce4-terminal`, `xfce4-settings-manager` and `chromium`;
this lane makes them MetaOS: our names, our dock, our start page.

**Label: CODE-INSPECTED.** Verify the whole lane with
`iso/tools/verify_lane.sh`, which runs the static checker and every ISO test
file and ends in `LANE GREEN` or `LANE RED`. The configs are parsed and checked by
`iso/tools/check_iso_config.py`. Nothing here has been clicked in a live
session — this Mac has no VM, so the H+6 line "each app opens from the dock,
does its job, closes clean" stays **UNPROVEN** until a VM run.

## Files

| File | Goes to | What it does |
|---|---|---|
| `desktop/meta-*.desktop` | `/usr/share/applications/` | five launchers: Files, Terminal, Settings, Web, Agent status |
| `plank/meta-*.dockitem` | `/usr/share/metaos/dock/` | the dock order; `meta-first-login` copies these into the real home |
| `chromium/policies.json` | `/etc/chromium/policies/managed/metaos.json` | start page, no first-run tab |
| `chromium/meta-start.html` | `/usr/share/metaos/start/` | the start page itself, works offline |
| `chromium/tokens.css` | `/usr/share/metaos/start/` | generated from the frozen contract, never hand-edited |
| `agent-status/meta-agent-status.py` | `/usr/local/bin/` | the agent-layer status reader |

## Install

```sh
iso/tools/apply.sh --root /                  # the whole lane, into a live root
iso/tools/apply.sh --root /tmp/stage --verify # or a staging tree, then checked
```

`apply.sh` is the only install path. It records every file it writes, can
revert exactly that set, and runs the doctor against the result when asked.

After that, `chromium` opens on the Meta start page and the dock shows five
apps in the order listed.

## Choices worth knowing

- Colours come from `iso/contracts/tokens.json`, the frozen contract on
  `opencode1/metaos-1.0` (pinned in `iso/contracts/PIN.md`). The page links a
  generated `tokens.css` and carries no hex of its own, so the theme lane can
  recolor it without either of us touching the other's files.
- The start page is `file://` and self-contained: no fonts, images or
  scripts from the network, so it renders on a machine with no cable.
- The search box posts to DuckDuckGo. It is the one thing on the page that
  needs a network, and the page says so above it.
- `RestoreOnStartup: 4` means "open this list" — Chromium's own first-run
  tab is turned off, so the first window is ours.
- Dock items point at the `.desktop` files by absolute path, which is what
  Plank reads; renaming an app means editing its dockitem too.

## The fifth app — agent-status

The frozen launcher set is `files, terminal, settings, browser, agent-status`
(`metaos-contracts/APPS.md`). All five ship here now. The first four are
Xubuntu binaries; the fifth is ours:

    meta-agent-status [--root DIR] [--json] [--stale-after SECONDS]

It reads the local agent layer and prints what it finds: how many agents the
registry holds, how old the watchman heartbeat is, how many jobs are queued,
and how many lines the gym ledger, the inbox and the refusal log carry. It
writes nothing and starts nothing. A file that is absent prints `absent`, and
a required file that is missing makes the command exit 1 with the row named.

`--root` defaults to `$METAOS_ROOT`, or `/opt/metaos` when that is unset, so
the reader works on a checkout (`--root .`) and on an installed system
without a code change. `--json` is the machine-readable form for the agent
layer itself to consume.

The launcher uses `Terminal=true` because the program prints a table. Tests:
`python3 tests/test_iso_agent_status.py` (10 cases, real directories, no
mock).

It ships: `meta-agent-status.desktop` and the fifth dock item are in this lane
from `9020439c`, and the checker fails if either goes missing.
