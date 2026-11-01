# UI screenshot pack — HN-021

## Status: BLOCKED — no captures exist yet

No headless browser exists in the sandbox where this branch was
built: no `chromium`, `google-chrome`, or `firefox` binary, no
Playwright, no `node_modules`. Nothing here is a screenshot, and
no capture is claimed. This file is the shot list plus the capture
script for a Mac run, so the pack can be completed at gate without
re-deciding what to shoot.

## Capture script

`scripts/capture-ui-screenshots.sh <label> [outdir]` — starts the
server (`node server/server.mjs`, port 8080) if it is not already
listening, then takes two full-page captures with Chrome headless:
desktop 1440×900 and mobile 390×844. Run it once per tip:

```
./scripts/capture-ui-screenshots.sh before docs/screenshots
git checkout hana/ui-wave-2
./scripts/capture-ui-screenshots.sh after docs/screenshots
```

The six surfaces below are framed from those two captures plus
the manual steps listed per surface (the CLI cannot click into
the console view or open the help overlay on its own).

## The six surfaces

### 1. Command topbar + live ribbon (HN-011)
Frame: command view, top of the left rail — `#cmd-ribbon` above
the Loop feed heading, with the topbar product chips and
`#cmd-ai-focus`. Before: no ribbon (the rail starts at the Loop
feed heading). After: the ribbon shows the newest incident.

### 2. Left rail: queue, cameras, loop feed (HN-012/013/014)
Frame: the full left rail with an empty store — the six designed
empty states (queue, inspector note, loop feed, camera wall,
camera list, session log). Then kill the crew server mid-session
for the loop-feed error row with its Retry button (HN-014 test
does this live; the shot repeats it by hand).

### 3. Inspector + pin card (HN-019)
Frame: the right rail inspector with a selected camera, and the
open pin card. Show the pin card's Close button focused after
opening (keyboard walk: focus lands on Close, returns on close).

### 4. Camera wall (HN-016/017)
Frame: `#cmd-wall` — desktop row, then the 390 px capture where
the wall stacks vertically. With reduced motion on, the wall
snapshot loads once and does not auto-cycle (HN-017).

### 5. Console panels + help overlay (HN-015/018)
Frame: the console view (click "Console view") — the panels with
their fixed text colors (HN-018: vigiles/ignis/error text, dark
primary text), then the help overlay open (click "Keyboard
shortcuts") listing the three shortcuts with `<kbd>` styling.

### 6. Mobile 390 px stacked view (HN-016)
Frame: the 390×844 capture — wall stacked, 44 px tap targets,
no horizontal scroll. This is the shot the rule-verified mobile
pass (HN-016) still owes as device proof.

## Pairing rule

Every surface ships as a before/after pair with the same viewport
and the same store state. Before = `origin/main` at capture time;
after = this branch's tip. Do not mix viewports or store states
between the two halves of a pair.
