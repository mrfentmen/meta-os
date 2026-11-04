# MetaOS terminal defaults — README

## Install path

- Source (this tree): `os-build/iso/payload-theme/terminal/metaos-terminal-profile.txt`
  (byte-identical mirror at `metaos-theme/terminal/metaos-terminal-profile.txt`).
- Installed reference copy: `/usr/share/doc/metaos/terminal-profile.txt`
  (inspection only — **nothing reads this file as code**).
- Live default: `/etc/xdg/xfce4/terminal/terminalrc`, written by the face-lane
  provision step (`os-build/face/provision.sh`, section "1a4b") from these same
  values, then copied into `/etc/skel` and each home directory on first provision.
  An existing `terminalrc` is never overwritten, so a user's own colours survive.

## What reads it

- A person, verifying the dark-terminal values.
- `terminal/check_profile.sh --check` (this directory): parses both copies as
  key/value files, rejects duplicates, unknown keys, and stock-distro-named fonts.
- The provision step reads the *values*, not this file (it embeds its own copy;
  see the report's cross-lane request to change its `FontName` line).

## When it is missing

- The reference copy: nothing breaks; it is documentation.
- The live `/etc/xdg/xfce4/terminal/terminalrc`: xfce4-terminal falls back to
  its stock light theme (white background). That is the "two terminals, two
  looks" failure the provision step was written to prevent.

## The prompt (not set here)

No file in this directory sets `PS1`. The contracted prompt (blue `metaos` +
working directory, no `user@host`) is appended to the login bashrc files by
`os-build/tools/fix_terminal_prompt.sh` (OS-4 tool, read-only from this lane).
Rendered string: ESC `[38;5;33m` + `metaos` + reset + ` ` + ESC `[38;5;111m` +
cwd + reset + `$ `.
