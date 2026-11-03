# Base image lane

The package manifest a MetaOS base image consumes, and the line every other
lane appends to. It follows the format frozen in
`metaos-contracts/PACKAGES.md`: one apt package per line, `#fetch <url>
<dest>` for a file.

## What is here

`metaos.packages` — what a Cubic remaster must install on top of Xubuntu
24.04.5. Two groups: what the shell and theme lane needs (`plank`,
`fonts-inter`, `lightdm-gtk-greeter`) and what the boot and install lane needs
(`plymouth`, `calamares`). The base image already carries the four desktop
programs, so they are not repeated.

## The `#base:` line

Xubuntu already ships the four programs the launchers start. Naming them on a
single `#base:` line is what lets a checker prove this: every `Exec=` in a
`.desktop` file must resolve to a package in this file, a binary on that line,
or a program the lane ships itself. A launcher for a program nobody installs
is a dead icon, and this is how that gets caught before an install.

## What this lane does not do

It does not create the ISO, does not run `cubic`, and does not create a user.
Calamares makes the account at install time (`iso/calamares/modules/users.conf`).
Package *names* are checked for shape and coverage here; whether apt can
resolve them is settled by the base build, on the machine that has the archive
and the network.

**Status: CODE-INSPECTED.** Nothing here has been installed or booted.

## Check it

```
python3 iso/tools/check_iso_config.py     # the base: and apps: lines
iso/tools/verify_lane.sh                  # whole lane
```
