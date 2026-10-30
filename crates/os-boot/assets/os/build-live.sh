#!/bin/bash
# os/build-live.sh -- OS-008 fallback pipeline, one command.
#
# Usage (from the repo root, as root): os/build-live.sh
# Output: os/metaos-<date>.iso + os/metaos-<date>.iso.sha256
#
# Steps:
#   1. Refuse a dirty checkout: the pipeline builds from a clean
#      checkout only, so a produced ISO always matches a commit.
#   2. Require root (live-build mounts and chroots) and the tools
#      lb, mksquashfs, xorriso, sha256sum.
#   3. Stage the OS glue into live-build/config/includes.chroot/
#      from this repo's own os/services/, os/firstboot/, and
#      os/bin/ (units, target, firstboot program, tools). The
#      staged copies are build inputs only: a trap removes the
#      whole staged tree on exit, so the repo never carries a
#      second copy of a unit. The committed sources are read,
#      never written.
#   3b. OS-059 gateway bake staging: same allowlist and stamp
#      as os/build-image.sh section 2b (gateway.py plus
#      backends.json only, from the workspace mcp-gateway
#      checkout or $METAOS_GATEWAY_SRC), staged under
#      includes.chroot/opt/relay/mcp-gateway/ so the ISO
#      carries the daemon beside /opt/relay. The hook enables
#      the unit; this staging supplies the files it runs.
#   4. lb clean, lb config (reads live-build/auto/config), then
#      lb build in os/live-build/.
#   5. Rename live-image-amd64.hybrid.iso to metaos-<date>.iso
#      and write its .sha256 beside it.
#
# NOT proven in the sandbox: this script has never run end to end
# here (no lb, no mksquashfs, no xorriso). The first real run
# belongs on a build host with live-build plus root; until then
# the pipeline is config plus wrapper plus structural tests, not
# a proven build. A boot of the ISO in QEMU to the crew session
# is still owed, as is the OS-010 version pin against the ISO's
# package list.
set -euo pipefail
cd "$(dirname "$0")"
REPO_ROOT="$(cd .. && pwd)"
DATE=$(date +%F)
ISO="metaos-$DATE.iso"

[ -z "$(git -C "$REPO_ROOT" status --porcelain)" ] || {
  echo "refusing: checkout is dirty - commit or stash first" >&2
  exit 1
}
[ "$(id -u)" = "0" ] || {
  echo "refusing: live-build needs root for its chroot mounts" >&2
  exit 1
}
for tool in lb mksquashfs xorriso sha256sum; do
  command -v "$tool" >/dev/null 2>&1 || {
    echo "missing tool: $tool" >&2
    exit 1
  }
done

BUILD_DIR="live-build"
STAGE="$BUILD_DIR/config/includes.chroot"
mkdir -p "$STAGE/etc/systemd/system" "$STAGE/usr/local/bin"
cleanup() {
  rm -rf "$STAGE"
}
trap cleanup EXIT

cp services/*.service services/*.timer services/relay.target \
  "$STAGE/etc/systemd/system/"
cp firstboot/metaos-firstboot bin/metaos-boot-checklist bin/metaos-update \
  "$STAGE/usr/local/bin/"
chmod 755 "$STAGE/usr/local/bin/"*

# OS-059: gateway bake staging (allowlist + stamp, see 3b above).
GATEWAY_SRC="${METAOS_GATEWAY_SRC:-$(cd "$REPO_ROOT/../.." && pwd)/mcp-gateway}"
[ -f "$GATEWAY_SRC/gateway.py" ] || { echo "refusing: no gateway.py in $GATEWAY_SRC" >&2; exit 1; }
[ -f "$GATEWAY_SRC/backends.json" ] || { echo "refusing: no backends.json in $GATEWAY_SRC" >&2; exit 1; }
mkdir -p "$STAGE/opt/relay/mcp-gateway"
cp "$GATEWAY_SRC/gateway.py" "$GATEWAY_SRC/backends.json" "$STAGE/opt/relay/mcp-gateway/"
{
  echo "gateway-bake $DATE"
  echo "source $GATEWAY_SRC"
  (cd "$STAGE/opt/relay/mcp-gateway" && sha256sum gateway.py backends.json)
} > "$STAGE/opt/relay/mcp-gateway/.metaos-gateway-bake"

# OS-083: artifact store root staging, same empty-plus-marker
# shape as the debootstrap route (see os/build-image.sh 2c).
# Ownership on the live route is set by the live hook
# (0900-metaos-services.hook.chroot), which runs as root inside
# the chroot: this staging dir carries no artifact and no
# credential, only the marker, so nothing sensitive is staged.
mkdir -p "$STAGE/var/lib/metaos/artifacts"
{
  echo "artifact-store-root /var/lib/metaos/artifacts"
  echo "git-init on first deposit by mos/artifact_store.py"
} > "$STAGE/var/lib/metaos/artifacts/.metaos-artifact-store"

# OS-078: memory store root staging, same empty-plus-marker
# shape as the debootstrap route (see os/build-image.sh 2d).
# Ownership on the live route is set by the live hook
# (0900-metaos-services.hook.chroot), which runs as root inside
# the chroot: this staging dir carries no memory entry and no
# credential, only the marker, so nothing sensitive is staged.
mkdir -p "$STAGE/var/lib/metaos/memory"
{
  echo "memory-store-root /var/lib/metaos/memory"
  echo "namespaces ensured at boot by relay-memory.service"
} > "$STAGE/var/lib/metaos/memory/.metaos-memory-store"

# OS-065: skills collection root staging, same empty-plus-marker
# shape as the debootstrap route (see os/build-image.sh 2e).
# Ownership on the live route is set by the live hook
# (0900-metaos-services.hook.chroot), which runs as root inside
# the chroot: this staging dir carries no skill content and no
# credential, only the marker, so nothing sensitive is staged.
mkdir -p "$STAGE/var/lib/metaos/skills"
{
  echo "skills-collection-root /var/lib/metaos/skills"
  echo "populated by a later install step, never baked with skill content"
} > "$STAGE/var/lib/metaos/skills/.metaos-skills-root"

cd "$BUILD_DIR"
lb clean
lb config
lb build

[ -s "live-image-amd64.hybrid.iso" ] || {
  echo "live-build produced no ISO in $BUILD_DIR" >&2
  exit 1
}
mv "live-image-amd64.hybrid.iso" "../$ISO"
cd ..
sha256sum "$ISO" > "$ISO.sha256"
echo "built $ISO"
cat "$ISO.sha256"
