#!/bin/sh
# Meta OS terminal identity.
#
# Two things were wrong inside the image:
#
#   1. The prompt read `ubuntu@metaos` in Ubuntu's green. The live user is
#      still `ubuntu` (autologin, home, sudoers all keyed on it), so the
#      honest fix is the prompt, not a rename under a running system: it says
#      `metaos` in Meta blue and drops the user@host pair entirely.
#
#   2. /etc/bash.bashrc.d/metaos.sh was installed but never executed --
#      Ubuntu's /etc/bash.bashrc has no drop-in loop, so the spinning-logo
#      hook in there has never run once. We add the loop, guarded, so any
#      future drop-in also works.
#
# The prompt is appended to the END of each bashrc on purpose: it must run
# after Ubuntu's own colour block, and the last assignment wins. No python,
# no sed replacement escaping -- append-only, so this works in a bare
# container and in the guest.
#
# Usage: sh fix_terminal_prompt.sh [ROOT]      (default /mnt)
set -eu

ROOT="${1:-/mnt}"
[ -d "$ROOT/etc" ] || { echo "fix_terminal_prompt: no $ROOT/etc" >&2; exit 1; }

MARK="# metaos: shell identity (appended by os-build/tools/fix_terminal_prompt.sh)"

for f in "$ROOT/etc/skel/.bashrc" "$ROOT/home/meta/.bashrc" "$ROOT/home/ubuntu/.bashrc"; do
  [ -f "$f" ] || continue
  if grep -qF "$MARK" "$f"; then
    echo "prompt: already set in ${f#"$ROOT"}"
    continue
  fi
  cat >>"$f" <<'EOF'

# metaos: shell identity (appended by os-build/tools/fix_terminal_prompt.sh)
# Runs last, so it wins over the base image's \u@\h prompt above. 38;5;33 is Meta
# blue; the path is a lighter blue so the two never blur together.
PS1='\[\033[38;5;33m\]metaos\[\033[0m\] \[\033[38;5;111m\]\w\[\033[0m\]\$ '
EOF
  echo "prompt: set in ${f#"$ROOT"}"
done

# The drop-in loop. Appended once, guarded so re-running is a no-op.
BASHRC="$ROOT/etc/bash.bashrc"
if [ -f "$BASHRC" ] && ! grep -q 'metaos: source drop-in shell hooks' "$BASHRC"; then
  cat >>"$BASHRC" <<'EOF'

# metaos: source drop-in shell hooks (the base image hooks none in, which
# is why /etc/bash.bashrc.d/metaos.sh never ran).
if [ -d /etc/bash.bashrc.d ]; then
  for _metaos_dropin in /etc/bash.bashrc.d/*.sh; do
    [ -r "$_metaos_dropin" ] && . "$_metaos_dropin"
  done
  unset _metaos_dropin
fi
EOF
  echo "bashrc.d: hook loop appended to /etc/bash.bashrc"
else
  echo "bashrc.d: hook loop already present (or no bash.bashrc)"
fi

# Receipt: show the prompt line that is now in effect.
echo "--- effective prompt ---"
# Show it for whoever actually logs in: meta first, the legacy ubuntu path
# only if this root still has one (it does not, since the rename).
for _f in "$ROOT/home/meta/.bashrc" "$ROOT/home/ubuntu/.bashrc"; do
  [ -f "$_f" ] && grep -h '^PS1=' "$_f" | tail -1
  [ -f "$_f" ] && break
done
echo "fix_terminal_prompt: done"
