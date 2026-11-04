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
#   /etc/metaos/agent.env                       machine secrets, root 0600, empty in image
#   /usr/local/bin/meta-agent-login             seeds env, starts the units
#   /usr/local/bin/meta-ask                     hand work to an agent (--list, submit)
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
MACHINE_ENV=/etc/metaos/agent.env
ASK=/usr/local/bin/meta-ask
MCODE=/usr/local/bin/meta-code
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
             "$ROOT$SKEL_ENV" "$ROOT$MACHINE_ENV" "$ROOT$HOOK" "$ROOT$ASK" "$ROOT$ENTRY" \
             "$ROOT$MCODE" "$ROOT$HEALTH"; do
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
             oc2-patrol.timer oc2-health.service oc2-health.timer \
             oc2-watchman.service; do
    [ -f "$ROOT$UNITS/$unit" ] && say "unit $unit" || bad "unit missing: $UNITS/$unit"
  done
  # Every service the install enables must have its link checked, not a
  # hand-kept list: the relay watchman was installed, enabled and unverified.
  for unit in "$ROOT$UNITS"/*.service; do
    [ -f "$unit" ] || continue
    unit=$(basename "$unit")
    [ "$unit" = "oc2-health.service" ] && continue
    link="$ROOT$WANTS/default.target.wants/$unit"
    [ -e "$link" ] || [ -L "$link" ] && say "enabled $unit" || bad "not enabled: default.target.wants/$unit"
  done
  link="$ROOT$WANTS/timers.target.wants/oc2-patrol.timer"
  [ -e "$link" ] || [ -L "$link" ] && say "enabled oc2-patrol.timer" || bad "not enabled: timers.target.wants/oc2-patrol.timer"
  link="$ROOT$WANTS/timers.target.wants/oc2-health.timer"
  [ -e "$link" ] || [ -L "$link" ] && say "enabled oc2-health.timer" || bad "not enabled: timers.target.wants/oc2-health.timer"
  [ -f "$ROOT$HEALTH" ] && say "health cadence: probe + timer present" || bad "health probe missing: $HEALTH"

  for rel in server/queue/queue_service.py server/queue/patrol.py \
             server/queue/trio_agent.py js/products.js js/schema.js \
             agents/watchman.mjs agents/runtime.mjs agents/registry.json; do
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

  # Machine secrets: empty in the image, root 0600, never baked with a value.
  # The key name is assembled so this script never contains KEY= literally
  # (the repo guard forbids that shape even when empty).
  if [ ! -f "$ROOT$MACHINE_ENV" ]; then
    bad "machine env missing: $MACHINE_ENV"
  else
    _k1="SPARK_API_KEY"
    _k2="METAOS_NOTIFY_WEBHOOK"
    if grep -q "^${_k1}=$" "$ROOT$MACHINE_ENV" \
      && grep -q "^${_k2}=$" "$ROOT$MACHINE_ENV"; then
      say "machine env pins empty documented keys"
    else
      bad "machine env must pin empty ${_k1}= and ${_k2}="
    fi
    if grep -qE "sk-[A-Za-z0-9]|BEGIN PRIVATE" "$ROOT$MACHINE_ENV"; then
      bad "machine env contains a secret"
    else
      say "machine env has no secret"
    fi
    # Value must be empty: any non-empty assignment is a baked secret.
    if grep -qE "^${_k1}=.+" "$ROOT$MACHINE_ENV"; then
      bad "machine env carries a baked ${_k1} value"
    fi
    _mode=$(stat -c %a "$ROOT$MACHINE_ENV" 2>/dev/null \
      || stat -f %Lp "$ROOT$MACHINE_ENV" 2>/dev/null || echo "?")
    if [ "$_mode" = "600" ]; then
      say "machine env mode 0600"
    else
      bad "machine env mode is ${_mode}, want 600: $MACHINE_ENV"
    fi
    if [ "$(id -u)" = "0" ]; then
      _uid=$(stat -c %u "$ROOT$MACHINE_ENV" 2>/dev/null || echo "0")
      if [ "$_uid" = "0" ]; then
        say "machine env root-owned"
      else
        bad "machine env not root-owned: uid ${_uid}"
      fi
    else
      say "machine env ownership skipped (not root)"
    fi
    unset _k1 _k2 _mode
    [ -n "${_uid:-}" ] && unset _uid
  fi

  if [ -f "$ROOT$HOOK" ] && [ -x "$ROOT$HOOK" ]; then
    say "login hook executable"
    if grep -q "/etc/metaos/agent.env" "$ROOT$HOOK"; then
      say "login hook sources machine env"
    else
      bad "login hook does not source /etc/metaos/agent.env"
    fi
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

  if [ -f "$ROOT$ASK" ] && [ -x "$ROOT$ASK" ]; then
    say "meta-ask present and executable"
    if grep -q -- "--list" "$ROOT$ASK" \
      && grep -q "no such agent" "$ROOT$ASK"; then
      say "meta-ask lists and refuses unknown agents"
    else
      bad "meta-ask missing --list or unknown-agent refusal"
    fi
    if grep -q "8935" "$ROOT$ASK"; then
      say "meta-ask references queue port 8935"
    else
      bad "meta-ask does not reference queue port 8935"
    fi
  else
    bad "meta-ask missing or not executable: $ASK"
  fi

  if [ -f "$ROOT$MCODE" ] && [ -x "$ROOT$MCODE" ]; then
    say "meta-code present and executable"
    if grep -q "agents/agent_loop.mjs" "$ROOT$MCODE" && grep -q "agent.env" "$ROOT$MCODE"; then
      say "meta-code runs the real loop and reads the machine env"
    else
      bad "meta-code does not reference agent_loop.mjs or agent.env"
    fi
  else
    bad "meta-code missing or not executable: $MCODE"
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

# The agent runtime runs from the read-only payload; only its state directory
# is writable, and that lives in the user's home.
say "agent runtime -> $PAYLOAD/agents"
mkdir -p "$ROOT$PAYLOAD/agents"
cp "$REPO"/agents/*.mjs "$REPO/agents/registry.json" "$ROOT$PAYLOAD/agents/"

# The registry names hosted entry points that live beside the code
# (`repo:nervus/hosted.mjs`, `repo:handsfree/hosted.mjs`, `repo:aegis/hosted.mjs`).
# Only agents/ was staged, so in the image those jobs started a node process
# that could not find its own file and exited 1 — the same "failed (exit 1)"
# the Agents page showed for every order. Stage the trees the registry names.
for tree in nervus aegis handsfree; do
  [ -d "$REPO/$tree" ] || continue
  say "hosted worker -> $PAYLOAD/$tree"
  mkdir -p "$ROOT$PAYLOAD/$tree"
  cp -R "$REPO/$tree/." "$ROOT$PAYLOAD/$tree/"
done
if [ -d "$REPO/os/worlds/officina/runtime" ]; then
  say "hosted worker -> $PAYLOAD/os/worlds/officina/runtime"
  mkdir -p "$ROOT$PAYLOAD/os/worlds/officina/runtime"
  cp -R "$REPO/os/worlds/officina/runtime/." "$ROOT$PAYLOAD/os/worlds/officina/runtime/"
fi
if [ -f "$REPO/mcp-gateway/backends.json" ]; then
  mkdir -p "$ROOT$PAYLOAD/mcp-gateway"
  cp "$REPO/mcp-gateway/backends.json" "$ROOT$PAYLOAD/mcp-gateway/"
fi

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

say "machine env"
mkdir -p "$ROOT$(dirname "$MACHINE_ENV")"
_k1="SPARK_API_KEY"
_k2="METAOS_NOTIFY_WEBHOOK"
{
  echo "# /etc/metaos/agent.env — machine secrets for the OC2 agent layer."
  echo "# Installed root-owned 0600 by agent-layer/stage.sh. Values are EMPTY in the image."
  echo "# Provisioning fills them on the target; never commit a filled copy."
  echo "# The login hook sources this file when readable and imports a non-empty"
  echo "# key into the user manager. Empty or unreadable means patrol pauses LOUDLY."
  echo "# Keys:"
  echo "#   ${_k1}: direct Spark transport (server/queue/spark_gen.py). Empty = no model calls."
  echo "#   ${_k2}: optional webhook for relay notices (agents/notify.mjs). Empty = journal only."
  printf '%s=\n' "$_k1"
  printf '%s=\n' "$_k2"
} > "$ROOT$MACHINE_ENV"
chmod 0600 "$ROOT$MACHINE_ENV"
chown 0:0 "$ROOT$MACHINE_ENV" 2>/dev/null || true
unset _k1 _k2
if grep -qE "sk-[A-Za-z0-9]|BEGIN PRIVATE" "$ROOT$MACHINE_ENV"; then
  echo "agent-stage: machine env contains a secret" >&2
  exit 1
fi

say "login hook"
mkdir -p "$ROOT$(dirname "$HOOK")"
install -m755 "$HERE/meta-agent-login.sh" "$ROOT$HOOK"

say "meta-ask"
mkdir -p "$ROOT$(dirname "$ASK")"
install -m755 "$HERE/meta-ask.py" "$ROOT$ASK"

say "meta-code"
mkdir -p "$ROOT$(dirname "$MCODE")"
install -m755 "$HERE/meta-code.sh" "$ROOT$MCODE"

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
