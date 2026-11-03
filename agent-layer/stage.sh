#!/bin/sh
# stage.sh — put the OC2 agent layer into a root filesystem, offline.
#
# The agent layer used to exist only as `install.sh`, which assumes the repo is
# checked out in the user's home and systemd is running. An ISO has neither.
# This stages the runtime, the four user units, the env template and the login
# hook into a root tree, and creates the `.wants` symlinks by hand so nothing
# needs a daemon at build time.
#
#   stage.sh <root>            stage into <root>
#   stage.sh <root> --check    verify an already staged root
#   stage.sh <root> --list     print every path staged, for apply.sh's manifest
#
# Layout inside <root>:
#   /usr/share/metaos/agent/server/queue/*.py   runtime (REPO_ROOT = agent/)
#   /usr/share/metaos/agent/js/{products,schema}.js
#   /usr/share/metaos/agent/env                 template for new users
#   /usr/lib/systemd/user/oc2-*.{service,timer}
#   /etc/systemd/user/default.target.wants/...  enabled without a daemon
#   /etc/systemd/user/timers.target.wants/...
#   /etc/skel/.config/oc2-agent/env             what Calamares gives a new user
#   /usr/local/bin/meta-agent-login             seeds env, starts the units
#   /etc/xdg/autostart/meta-agent-login.desktop
#
# Run as root on the build host; it touches only <root>. `--check` runs as
# anyone and writes nothing.
set -eu

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO=$(dirname "$HERE")
ROOT=${1:-}
MODE=stage

usage() {
  echo "usage: stage.sh <root> [--check]" >&2
}

[ -n "$ROOT" ] || { usage; exit 2; }
if [ "${2:-}" = "--check" ]; then
  MODE=check
elif [ "${2:-}" = "--list" ]; then
  MODE=list
elif [ -n "${2:-}" ]; then
  usage
  exit 2
fi

PAYLOAD=/usr/share/metaos/agent
UNITS=/usr/lib/systemd/user
WANTS=/etc/systemd/user
SKEL_ENV=/etc/skel/.config/oc2-agent/env
HOOK=/usr/local/bin/meta-agent-login
HEALTH=/usr/local/lib/metaos/meta-agent-health.py
ENTRY=/etc/xdg/autostart/meta-agent-login.desktop
CHECKOUT=/usr/share/metaos/agent

fail=0
say() { echo "agent-stage: $*"; }
bad() { echo "agent-stage: FAIL $*" >&2; fail=1; }

if [ "$MODE" = "list" ]; then
  # apply.sh records what it installed so --revert can remove exactly that.
  # Printing the staged paths here keeps the two from drifting: the stager is
  # the only thing that knows what it wrote.
  [ -d "$ROOT" ] || { echo "agent-stage: not a directory: $ROOT" >&2; exit 2; }
  {
    find "$ROOT$PAYLOAD" -type f 2>/dev/null | sed "s|^$ROOT||"
    for f in "$ROOT$UNITS"/*.service "$ROOT$UNITS"/*.timer \
             "$ROOT$SKEL_ENV" "$ROOT$HOOK" "$ROOT$ENTRY" \
             "$ROOT$HEALTH"; do
      [ -f "$f" ] && echo "${f#$ROOT}"
    done
    for l in "$ROOT$WANTS"/*/*; do
      [ -L "$l" ] && echo "${l#$ROOT}"
    done
  } | sort -u
  exit 0
fi

if [ "$MODE" = "check" ]; then
  for unit in oc2-queue.service oc2-trio.service oc2-patrol.service \
             oc2-patrol.timer oc2-health.service oc2-health.timer; do
    [ -f "$ROOT$UNITS/$unit" ] && say "unit $unit" || bad "unit missing: $UNITS/$unit"
  done
  for unit in oc2-queue.service oc2-trio.service oc2-patrol.service; do
    link="$ROOT$WANTS/default.target.wants/$unit"
    [ -e "$link" ] || [ -L "$link" ] && say "enabled $unit" || bad "not enabled: default.target.wants/$unit"
  done
  link="$ROOT$WANTS/timers.target.wants/oc2-patrol.timer"
  [ -e "$link" ] || [ -L "$link" ] && say "enabled oc2-patrol.timer" || bad "not enabled: timers.target.wants/oc2-patrol.timer"
  link="$ROOT$WANTS/timers.target.wants/oc2-health.timer"
  [ -e "$link" ] || [ -L "$link" ] && say "enabled oc2-health.timer" || bad "not enabled: timers.target.wants/oc2-health.timer"
  [ -f "$ROOT$HEALTH" ] && say "health cadence: probe + timer present" || bad "health probe missing: $HEALTH"

  for rel in server/queue/queue_service.py server/queue/patrol.py \
             server/queue/trio_agent.py js/products.js js/schema.js; do
    [ -f "$ROOT$PAYLOAD/$rel" ] && say "runtime $rel" || bad "runtime missing: $PAYLOAD/$rel"
  done

  if [ ! -f "$ROOT$SKEL_ENV" ]; then
    bad "env missing: $SKEL_ENV"
  else
    grep -q "^OC2_CHECKOUT=$CHECKOUT$" "$ROOT$SKEL_ENV" \
      && say "env pins OC2_CHECKOUT=$CHECKOUT" \
      || bad "env does not pin OC2_CHECKOUT=$CHECKOUT"
    if grep -qE "SPARK_API_KEY|sk-[A-Za-z0-9]|BEGIN PRIVATE" "$ROOT$SKEL_ENV"; then
      bad "env contains a secret"
    else
      say "env has no secret"
    fi
  fi

  if [ -f "$ROOT$HOOK" ] && [ -x "$ROOT$HOOK" ]; then
    say "login hook executable"
  else
    bad "login hook missing or not executable: $HOOK"
  fi

  if [ -f "$ROOT$ENTRY" ]; then
    exec_line=$(grep -m1 '^Exec=' "$ROOT$ENTRY" | cut -d= -f2-)
    try_line=$(grep -m1 '^TryExec=' "$ROOT$ENTRY" | cut -d= -f2-)
    if [ "$exec_line" = "$HOOK" ] && [ "$try_line" = "$HOOK" ]; then
      say "autostart entry resolves to the hook"
    else
      bad "autostart Exec/TryExec do not both equal $HOOK"
    fi
  else
    bad "autostart entry missing: $ENTRY"
  fi

  if [ "$fail" -ne 0 ]; then
    echo "agent-stage: FAILED" >&2
    exit 1
  fi
  say "PASS — agent layer staged correctly in $ROOT"
  exit 0
fi

# --- staging ------------------------------------------------------------
[ -d "$ROOT/etc" ] && [ -d "$ROOT/usr" ] || {
  echo "agent-stage: $ROOT is not a root filesystem (no /etc or /usr)" >&2
  exit 1
}

say "runtime -> $PAYLOAD"
mkdir -p "$ROOT$PAYLOAD/server/queue" "$ROOT$PAYLOAD/js"
cp "$REPO"/server/queue/*.py "$ROOT$PAYLOAD/server/queue/"
[ -f "$REPO/server/queue/README.md" ] && cp "$REPO/server/queue/README.md" "$ROOT$PAYLOAD/server/queue/"
[ -d "$REPO/server/queue/livecam_records" ] && cp -R "$REPO/server/queue/livecam_records" "$ROOT$PAYLOAD/server/queue/"
cp "$REPO/js/products.js" "$REPO/js/schema.js" "$ROOT$PAYLOAD/js/"

say "units -> $UNITS"
mkdir -p "$ROOT$UNITS"
cp "$REPO"/agent-layer/units/*.service "$REPO"/agent-layer/units/*.timer "$ROOT$UNITS/"

say "enabling without a daemon"
mkdir -p "$ROOT$WANTS/default.target.wants" "$ROOT$WANTS/timers.target.wants"
for unit in "$ROOT$UNITS"/*.service; do
  name=$(basename "$unit")
  # The health unit is timer-driven: enabling it in default.target would run
  # one check at login and never again.
  [ "$name" = "oc2-health.service" ] && continue
  ln -sfn "$UNITS/$name" "$ROOT$WANTS/default.target.wants/$name"
done
for unit in "$ROOT$UNITS"/*.timer; do
  name=$(basename "$unit")
  ln -sfn "$UNITS/$name" "$ROOT$WANTS/timers.target.wants/$name"
done

say "env template"
sed "s|^OC2_CHECKOUT=.*|OC2_CHECKOUT=$CHECKOUT|" "$REPO/agent-layer/env.example" > "$ROOT$PAYLOAD/env"
mkdir -p "$ROOT$(dirname "$SKEL_ENV")"
cp "$ROOT$PAYLOAD/env" "$ROOT$SKEL_ENV"
if grep -qE "SPARK_API_KEY|sk-[A-Za-z0-9]|BEGIN PRIVATE" "$ROOT$SKEL_ENV"; then
  echo "agent-stage: env template contains a secret" >&2
  exit 1
fi

say "login hook"
mkdir -p "$ROOT$(dirname "$HOOK")"
install -m755 "$HERE/meta-agent-login.sh" "$ROOT$HOOK"

say "health cadence"
mkdir -p "$ROOT$(dirname "$HEALTH")"
install -m755 "$HERE/meta-agent-health.py" "$ROOT$HEALTH"
mkdir -p "$ROOT$(dirname "$ENTRY")"
cat > "$ROOT$ENTRY" <<ENTRY_EOF
[Desktop Entry]
Type=Application
Name=MetaOS Agent Layer
Comment=Start the local queue, runner and patrol timer for this session
Exec=$HOOK
TryExec=$HOOK
Terminal=false
NoDisplay=true
OnlyShowIn=XFCE;
X-GNOME-Autostart-Delay=5
ENTRY_EOF

say "staged: $(find "$ROOT$PAYLOAD" -type f | wc -l | tr -d ' ') runtime files, $(ls "$ROOT$UNITS" | wc -l | tr -d ' ') units"
exit 0
