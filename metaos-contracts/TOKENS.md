# MetaOS frozen contracts v1 (OpenCode 1, 2026-11-02)
Every lane builds against THESE files, never against another lane's
output. Contracts change only by boss order, versioned below.

## 1. Colors (tokens.json — this dir, machine-readable)
blue #1877F2, white #EDF5FF, black #070B16, cyan #00C8FF,
violet #8B5CF6, pink #FF4F9A, emerald #20D6A3, gold #FFBD4A.
Bond builds pages to these tokens; my CSS is never his dependency.

## 2. Launcher app set (APPS.md — this dir, frozen list)
files, terminal, settings, browser, agent-status. Bond's configs and
my dock both reference these IDs; neither lane owns the other's files.

## 3. Package manifest format (PACKAGES.md — this dir)
Hana installs from `metaos.packages` (one apt package per line +
`#fetch` lines for files). Lanes ADD lines; nobody edits another
lane's lines. Format frozen; conflicts impossible by construction.

## 4. Autostart spec (AUTOSTART.md — this dir)
OpenCode 2 ships `/etc/xdg/autostart/metaos-*.desktop` entries running
only if their binary exists (`TryExec=`), degraded-off otherwise.
Buffy's fix never blocks OC2's install; broken runners ship disabled.

## 5. Proof naming (PROOFS.md — this dir)
`screenshots/<lane>/H<2|4|6|8|10|12>-<what>.png` + HMP screendumps.
Milo audits whatever exists at each cut; missing = named BLOCKED,
never a stall. Pax cuts ISOs at H+2/4/6/8/10/12 from lane branches
as they are — no lane holds the cut.
