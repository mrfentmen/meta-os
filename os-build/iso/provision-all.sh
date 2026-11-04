#!/bin/sh
# provision-all.sh — turn an unpacked MetaOS root filesystem into the real
# thing, in one command, in the one order that works.
#
#   sh os-build/iso/provision-all.sh <root> [--skip-packages] [--skip-identity]
#
# Every stage is idempotent. It stops recording at the first stage that fails
# but keeps going through the independent ones, then exits non-zero with a
# summary — one run tells you everything that is wrong instead of one thing.
#
# Why this file exists: the image used to be built by iso/provision.sh alone,
# which installs the branding and the installer but NOT the desktop face or its
# seven backends. That is why a themed image booted with no apps. The face
# provisioner is stage 4 here.
set -u

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO=$(CDPATH= cd -- "$HERE/../.." && pwd)
ROOT=${1:-}
[ -n "$ROOT" ] || { echo "usage: provision-all.sh <root> [--skip-packages] [--skip-identity]" >&2; exit 2; }
shift || true
[ -d "$ROOT/etc" ] || { echo "provision-all: $ROOT is not a root filesystem" >&2; exit 2; }

SKIP_PACKAGES=0
SKIP_IDENTITY=0
for a in "$@"; do
  case "$a" in
    --skip-packages) SKIP_PACKAGES=1 ;;
    --skip-identity) SKIP_IDENTITY=1 ;;
    *) echo "provision-all: unknown flag $a" >&2; exit 2 ;;
  esac
done

FAILED=""
TOTAL=0
step() { # step <number> <name> <command...>
  num=$1; name=$2; shift 2
  TOTAL=$((TOTAL + 1))
  echo ""
  echo "=== [$num] $name ==="
  if "$@"; then
    echo "=== [$num] OK $name"
  else
    echo "=== [$num] FAIL $name" >&2
    FAILED="$FAILED\n  [$num] $name"
  fi
}

# 1) packages the face and the relay need. Epiphany is the browser: on Ubuntu
# 24.04 chromium and firefox are snap shims, so there is no other apt choice.
# sudo is here because the image shipped without it: --no-install-recommends on
# a minimal base does not pull it, so `sudo` was "command not found" in the
# guest's own terminal while the account sat in the sudo group all along.
if [ "$SKIP_PACKAGES" = 0 ]; then
  step 1 "packages (webkit browser, node, git, window helpers)" \
    sh -c "chroot '$ROOT' env DEBIAN_FRONTEND=noninteractive apt-get update -qq &&
           chroot '$ROOT' env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
             epiphany-browser nodejs git curl xdotool wmctrl sudo"
else
  echo "=== [1] SKIP packages"
fi

# 2) the installer lane: plymouth, calamares, live extras
if [ -f "$HERE/provision.sh" ]; then
  step 2 "installer lane (plymouth, calamares, live extras)" \
    sh "$HERE/provision.sh" "$ROOT" --no-packages
else
  echo "=== [2] SKIP installer lane (no iso/provision.sh)"
fi

# 3) identity: GATED (identity lane, single-writer rule). dexubuntu's
# apply-in-chroot.sh addresses /etc absolutely: it must run INSIDE the
# chroot (Cubic phase), never here — running it now would brand the BUILD
# HOST's own /etc instead of $ROOT. $ROOT identity is already owned by step 2
# (provision.sh -> debrand.sh runs last, last writer wins at build time), so
# there is nothing for this step to add on the host.
if [ "$SKIP_IDENTITY" = 0 ]; then
echo "=== [3] SKIP dexubuntu on host (chroot-only; debrand owns $ROOT)"
  if [ -f "$REPO/os-build/metaos-brand/brand.sh" ]; then
    step 4 "branding (wallpaper, panel, dock, theme)" \
      sh "$REPO/os-build/metaos-brand/brand.sh" --root "$ROOT"
  elif [ -f "$HERE/payload-theme/apply.sh" ]; then
    step 4 "branding via payload-theme/apply.sh (greeter, backgrounds, gtk/xfwm4, panel, dock, icons)" \
      env METAOS_SKIP_IDENTITY=1 sh "$HERE/payload-theme/apply.sh" "$ROOT"
  else
    echo "=== [4] SKIP branding (no brand.sh, no payload-theme/apply.sh)"
  fi
else
  echo "=== [3][4] SKIP identity + branding"
fi

# 4c) identity re-stamp (identity lane, single-writer rule): step 4's theme
# apply writes its own identity copies (os-release without DOCUMENTATION_URL,
# motd naming the base). debrand.sh runs again last so $ROOT ends
# contract-correct; --check proves it.
if [ "$SKIP_IDENTITY" = 0 ]; then
  step "4c" "identity re-stamp (debrand last writer)" \
    sh "$REPO/os-build/identity/debrand.sh" --apply --root "$ROOT"
  step "4c-check" "identity re-stamp check" \
    sh "$REPO/os-build/identity/debrand.sh" --check --root "$ROOT"
fi

# 4b) fonts: the six vendored Meta families + fontconfig aliases. Installs
# files, not font packages: a font-package pull can reintroduce a non-Meta
# family name, so the image takes type from payload-theme/fonts/ instead.
step "4b" "fonts (Meta vendored)" sh "$HERE/payload-theme/fonts/install.sh" "$ROOT"

# 5) THE DESKTOP: the face, its seven backends, and the kiosk at login.
# This is the stage the old build was missing.
step 5 "desktop face + 7 backends + kiosk" sh "$REPO/os-build/face/provision.sh" --root "$ROOT"

# 6) the agent relay
step 6 "agent relay (queue, patrol, watchman, health)" sh "$REPO/agent-layer/stage.sh" "$ROOT"

# 7) metaosd: the API the Agent Status window reads.
if [ -f "$HERE/payload-agent/metaosd.mjs" ]; then
  step 7 "metaosd agent API" sh -c "
    install -m755 '$HERE/payload-agent/metaosd.mjs' '$ROOT/opt/face/metaosd.mjs' &&
    mkdir -p '$ROOT/usr/lib/systemd/user' &&
    cat > '$ROOT/usr/lib/systemd/user/metaosd.service' <<'UNIT'
[Unit]
Description=metaosd agent API 18940
After=network.target
[Service]
ExecStart=/usr/bin/node /opt/face/metaosd.mjs --port 18940
Restart=on-failure
[Install]
WantedBy=default.target
UNIT
    mkdir -p '$ROOT/usr/lib/systemd/user/default.target.wants' &&
    ln -sf '$ROOT/usr/lib/systemd/user/metaosd.service' \
           '$ROOT/usr/lib/systemd/user/default.target.wants/metaosd.service'"
else
  echo "=== [7] SKIP metaosd (no payload)"
fi

# 8) file ownership: everything staged as root belongs to the desktop user
DESKTOP_USER=$(awk -F: '$3>=1000 && $3<65534 {print $1; exit}' "$ROOT/etc/passwd")
if [ -n "${DESKTOP_USER:-}" ]; then
  step 8 "ownership for $DESKTOP_USER" sh -c "
    uid=\$(awk -F: -v u='$DESKTOP_USER' '\$1==u {print \$3}' '$ROOT/etc/passwd')
    gid=\$(awk -F: -v u='$DESKTOP_USER' '\$1==u {print \$4}' '$ROOT/etc/passwd')
    chown -R \$uid:\$gid '$ROOT/home/$DESKTOP_USER/.local' 2>/dev/null || true
    chown -R \$uid:\$gid '$ROOT/var/lib/lightdm' 2>/dev/null || true"
else
  echo "=== [8] SKIP ownership (no desktop user found)"
fi

echo ""
echo "=============================================="
if [ -z "$FAILED" ]; then
  echo "provision-all: $TOTAL stages, all OK"
  exit 0
fi
echo "provision-all: $TOTAL stages, FAILURES:$FAILED"
exit 1
