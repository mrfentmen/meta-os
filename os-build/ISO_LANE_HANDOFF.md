# ISO lane handoff — Bond, 2026-11-03

For Pax. Everything here is pushed; nothing is in `main`. Numbers are command
output, not estimates. No VM was started, because this machine has none.

## Commits on `bond/12h`

| Commit | Subject |
|---|---|
| `d2944778` | iso: stop branding.desc typing its own colours |
| `78ba1790` | iso: six lane features that were missing or fake |
| `355bc115` | iso: add a doctor that names the piece a bad install is missing |
| `dc6467ce` | iso: give the boot menu the same palette |
| `52804349` | iso: theme the login screen from the same palette |
| `00092db3` | iso: apply the dock and wallpaper at first login, not to /home/meta |
| `4ef3a69c` | iso: ship the base manifest and a generated theme |
| `bc880a74` | Turn the boot into one command and make the checker prove it bites |
| `df5b1664` | Record the measured RK-007 result, and leave a handoff for the next shift |
| `105de05f` | One command to install the whole lane into a base root, with a dry run |
| `9020439c` | Ship the fifth frozen app: a real agent-status reader, not a launcher pointing at nothing |
| `b6881336` | Build the ISO lane to the frozen token contract; name the fifth app as blocked |

## What each one unblocks

| Commit | Unblocks |
|---|---|
| boot kit + verdict tool | one command turns source into an image, and a serial log into PASS/FAIL rows — the 32GB MacBook run needs no guesswork |
| base manifest + theme | a launcher can no longer point at a program nothing installs; the desktop has a real wallpaper and GTK sheet from the frozen tokens |
| first-login fix | the dock and wallpaper now reach the account Calamares creates, which is the only account that exists |
| login screen | the ring survives the handoff from splash to greeter |
| boot menu | the first screen stops being stock GRUB |
| doctor | a failed install names its missing file instead of just looking wrong |
| six features | slideshow is real QML; `apply.sh` can revert and verify; checker speaks JSON |
| branding rule + proof plan | the last hand-typed colour is gone; the lane states which screenshots it owes |

## Merge order

1. `bond/12h` — one branch, everything above, gate green.
2. `bond/rk007` — builder fix and the cache untrack.
3. `bond/round13-records` — the 37 named IDs and three corrected counts.

`bond/12h` is self-contained: it does not import from `bond/rk007` except the
builder path that `boot_kit.sh` takes as an argument.

## What a merge does and does not buy

A merge buys: 138 static checks, 11 test files, a lane that installs into a
staging tree, verifies itself, and reverts cleanly.

A merge does not buy: a single proven pixel. Every visual claim in this lane is
CODE-INSPECTED until someone runs the boot. Say that in the post; do not let a
green gate read as a working ISO.

## If you pick it up next

1. Run `iso/tools/verify_lane.sh` on the merge result. It prints LANE GREEN or
   names what broke.
2. Ask OC2 where the agent layer installs; `meta-agent-status` defaults to
   `/opt/metaos`, and that default is the one guess in the app.
3. Run one boot on the 32GB MacBook: `iso/tools/boot_kit.sh --check` first, it
   names every missing tool before anything compiles.

## Known duplicate, not fixed here

Three welcome programs are in the tree. `apply.sh` installs
`iso/apps/welcome/meta-welcome.py`. Two orphans remain:
`metaos-theme/apps/metaos-welcome.py` and
`os-build/iso/payload-theme/apps/metaos-welcome.py`. Both are OC1's files and
carry hardcoded hexes, so this lane does not delete them. One of the two
should go before a cut, or the next reader has to work out which one ships.

