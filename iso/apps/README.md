# MetaOS core apps (Bond lane, H+6)

Launch configs only — no app is rewritten, no stub ships. Xubuntu already
has `thunar`, `xfce4-terminal`, `xfce4-settings-manager` and `chromium`;
this lane makes them MetaOS: our names, our dock, our start page.

**Label: CODE-INSPECTED.** The configs are parsed and checked by
`iso/tools/check_iso_config.py`. Nothing here has been clicked in a live
session — this Mac has no VM, so the H+6 line "each app opens from the dock,
does its job, closes clean" stays **UNPROVEN** until a VM run.

## Files

| File | Goes to | What it does |
|---|---|---|
| `desktop/meta-*.desktop` | `/usr/share/applications/` | four launchers: Files, Terminal, Settings, Web |
| `plank/meta-*.dockitem` | `~/.config/plank/dock1/launchers/` | the dock order |
| `chromium/policies.json` | `/etc/chromium/policies/managed/metaos.json` | start page, no first-run tab |
| `chromium/meta-start.html` | `/usr/share/metaos/start/` | the start page itself, works offline |

## Install

```sh
install -d /usr/share/applications /usr/share/metaos/start \
           /etc/chromium/policies/managed
cp iso/apps/desktop/*.desktop          /usr/share/applications/
cp iso/apps/chromium/meta-start.html   /usr/share/metaos/start/
cp iso/apps/chromium/policies.json     /etc/chromium/policies/managed/metaos.json
install -d /home/"$USER"/.config/plank/dock1/launchers
cp iso/apps/plank/*.dockitem /home/"$USER"/.config/plank/dock1/launchers/
```

After that, `chromium` opens on the Meta start page and the dock shows the
four apps in the order listed.

## Choices worth knowing

- The start page is `file://` and self-contained: no fonts, images or
  scripts from the network, so it renders on a machine with no cable.
- The search box posts to DuckDuckGo. It is the one thing on the page that
  needs a network, and the page says so above it.
- `RestoreOnStartup: 4` means "open this list" — Chromium's own first-run
  tab is turned off, so the first window is ours.
- Dock items point at the `.desktop` files by absolute path, which is what
  Plank reads; renaming an app means editing its dockitem too.
