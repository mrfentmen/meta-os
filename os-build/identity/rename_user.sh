#!/bin/sh
# rename the live user ubuntu -> meta.
#
# This is the last place Ubuntu's name is still visible to a person: the home
# folder appears in Files, in the prompt's working directory, in every path a
# person reads, and in the Places sidebar. The prompt already says `meta`, so
# the two disagreed.
#
# The uid does NOT change (still 1000), so file ownership survives the home
# move untouched. sudo, the desktop groups and the session units all key on the
# name, so they are rewritten too. Nothing here touches package metadata or
# apt -- rename the identity, keep the compatibility (same rule as debrand.sh).
#
#   sh os-build/identity/rename_user.sh /mnt            # apply
#   sh os-build/identity/rename_user.sh /mnt --check    # measure
set -eu

ROOT="${1:-/mnt}"
MODE=apply
[ "${2:-}" = "--check" ] && MODE=check
[ -d "$ROOT/etc" ] || { echo "rename_user: no $ROOT/etc" >&2; exit 2; }

OLD=ubuntu
NEW=meta

check() {
  fail=0
  say() { if [ "$2" = ok ]; then echo "PASS $1"; else echo "FAIL $1 -- $3"; fail=1; fi; }

  if grep -q "^$NEW:" "$ROOT/etc/passwd" 2>/dev/null; then
    say "passwd has $NEW" ok ""
  else
    say "passwd has $NEW" no "/etc/passwd has no $NEW entry"
  fi

  if grep -q "^$OLD:" "$ROOT/etc/passwd" 2>/dev/null; then
    say "passwd free of $OLD" no "a $OLD account still exists"
  else
    say "passwd free of $OLD" ok ""
  fi

  home=$(sed -n "s/^$NEW:[^:]*:[^:]*:[^:]*:[^:]*:\([^:]*\):.*/\1/p" "$ROOT/etc/passwd" 2>/dev/null)
  if [ -n "$home" ] && [ -d "$ROOT$home" ]; then
    say "home dir $home" ok ""
  else
    say "home dir" no "home '$home' is not a directory"
  fi

  if [ -d "$ROOT/home/$OLD" ]; then
    say "old home gone" no "/home/$OLD still exists"
  else
    say "old home gone" ok ""
  fi

  n=$(grep -rl "autologin-user=$OLD" "$ROOT/etc/lightdm" 2>/dev/null | wc -l | tr -d ' ')
  if [ "$n" = 0 ]; then say "autologin" ok ""; else say "autologin" no "$n lightdm conf(s) still say $OLD"; fi

  # The GECOS field (5th colon field) is the display name a person sees in the
  # greeter, in finger/getent, and in anything that prints a full name. Renaming
  # the account does not touch it, and it said "Ubuntu" for weeks after the
  # rename because nothing checked it.
  g=$(grep -c "^$NEW:[^:]*:[^:]*:[^:]*:[Uu]buntu:" "$ROOT/etc/passwd" 2>/dev/null || true)
  if [ "${g:-0}" = 0 ]; then
    say "display name" ok ""
  else
    say "display name" no "passwd still gives $NEW the full name Ubuntu"
  fi

  say "done" ok ""
  [ "$fail" = 0 ] || { echo "rename_user --check: FAIL"; exit 1; }
  echo "rename_user --check: PASS"
}

if [ "$MODE" = check ]; then check; exit 0; fi

echo "rename_user: $OLD -> $NEW in $ROOT"

# 1. account databases. Name columns only; uid/gid/home-with-new-name follow.
for db in passwd passwd- shadow shadow- group group- gshadow gshadow-; do
  f="$ROOT/etc/$db"
  [ -f "$f" ] || continue
  # leading name
  sed -i "s/^$OLD:/$NEW:/" "$f"
  # group member lists:  sudo:x:27:ubuntu  ->  sudo:x:27:meta
  sed -i "s/:$OLD\(,\|$\)/:$NEW\1/g" "$f"
  # home field, so the *.bak copies of passwd do not keep the old path
  sed -i "s|:/home/$OLD:|:/home/$NEW:|g" "$f"
  echo "  rewrote /etc/$db"
done

# supplementary id maps, if present
for f in "$ROOT/etc/subuid" "$ROOT/etc/subgid"; do
  [ -f "$f" ] || continue
  sed -i "s/^$OLD:/$NEW:/" "$f"
  echo "  rewrote ${f#"$ROOT"}"
done

# 2. the home directory itself (uid unchanged, so owners are already right)
if [ -d "$ROOT/home/$OLD" ] && [ ! -e "$ROOT/home/$NEW" ]; then
  mv "$ROOT/home/$OLD" "$ROOT/home/$NEW"
  echo "  moved /home/$OLD -> /home/$NEW"
fi

# 3. passwd home field is the new path only if the move happened
if [ -d "$ROOT/home/$NEW" ]; then
  sed -i "s|^$NEW:\([^:]*\):\([^:]*\):\([^:]*\):\([^:]*\):/home/$OLD:|$NEW:\1:\2:\3:\4:/home/$NEW:|" "$ROOT/etc/passwd"
fi

# 3b. the display name. Field 5 of passwd is the GECOS name; leaving it as
#     "Ubuntu" is Ubuntu's name still printed on a Meta account.
for db in passwd passwd-; do
  f="$ROOT/etc/$db"
  [ -f "$f" ] || continue
  if grep -q "^$NEW:[^:]*:[^:]*:[^:]*:[Uu]buntu:" "$f" 2>/dev/null; then
    sed -i "s/^\($NEW:[^:]*:[^:]*:[^:]*:\)[Uu]buntu:/\1Meta:/" "$f"
    echo "  display name -> Meta in /etc/$db"
  fi
done

# 4. autologin + live-session username
for f in $(grep -rl "autologin-user=$OLD" "$ROOT/etc/lightdm" 2>/dev/null); do
  sed -i "s/autologin-user=$OLD/autologin-user=$NEW/" "$f"
  echo "  autologin -> $NEW in ${f#"$ROOT"}"
done
if [ -f "$ROOT/etc/casper.conf" ] && grep -q "USERNAME=\"\?$OLD\"\?" "$ROOT/etc/casper.conf"; then
  sed -i "s/USERNAME=\"\?$OLD\"\?/USERNAME=\"$NEW\"/" "$ROOT/etc/casper.conf"
  echo "  casper USERNAME -> $NEW"
fi

# 5. anything still pointing a program at the old home
for d in "$ROOT/etc/systemd/system" "$ROOT/opt/face" "$ROOT/usr/share/metaos" \
         "$ROOT/home/$NEW/.config" "$ROOT/etc/skel/.config" \
         "$ROOT/home/$NEW/.local" "$ROOT/etc/skel/.local"; do
  [ -d "$d" ] || continue
  for f in $(grep -rl "/home/$OLD" "$d" 2>/dev/null); do
    sed -i "s|/home/$OLD|/home/$NEW|g" "$f"
    echo "  path fixed in ${f#"$ROOT"}"
  done
done

# 6. per-session crash logs carry the old path and nothing diagnostic that
#    matters after a rename; drop them so no file on screen says /home/ubuntu.
rm -f "$ROOT/home/$NEW/.xsession-errors" "$ROOT/home/$NEW/.xsession-errors.old" 2>/dev/null || true

echo "rename_user: applied; verifying"
check
