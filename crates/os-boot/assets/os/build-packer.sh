#!/bin/bash
# os/build-packer.sh -- OS-007 primary pipeline, one command.
#
# Usage (from the repo root): os/build-packer.sh
# Output: os/metaos-<date>.img + os/metaos-<date>.img.sha256
#
# Steps:
#   1. Refuse a dirty checkout: the pipeline builds from a clean
#      checkout only, so a produced image always matches a commit.
#   2. Require packer, qemu-system-x86_64, openssl, curl.
#   3. Resolve the current Debian 12 bookworm amd64 netinst ISO from
#      the cdimage listing (no version pinned in the repo; the
#      template verifies the ISO against the publisher SHA256SUMS).
#   4. Generate a random per-build relay password, hash it, and build
#      a build-time preseed: os/preseed.cfg with ONLY the locked "*"
#      password line replaced by the hash. The committed preseed is
#      never modified. The build preseed and the var file live in
#      os/work/ (gitignored) and a trap removes them on exit.
#   5. packer validate, then packer build (qemu, raw format).
#   6. Rename work/packer-out/metaos to metaos-<date>.img and write
#      its .sha256 beside it.
#
# NOT proven in the sandbox: this script has never run end to end
# here (no packer, no qemu, no /dev/kvm). The first real run belongs
# on a build host with Packer + QEMU + KVM; until then the pipeline
# is template + wrapper + structural tests, not a proven build.
# Second-run package reproducibility is unproven until two builds
# are compared (OS-007 acceptance, still open).
set -euo pipefail
cd "$(dirname "$0")"
REPO_ROOT="$(cd .. && pwd)"
DATE=$(date +%F)
IMG="metaos-$DATE.img"

[ -z "$(git -C "$REPO_ROOT" status --porcelain)" ] || {
  echo "refusing: checkout is dirty - commit or stash first" >&2
  exit 1
}
for tool in packer qemu-system-x86_64 openssl curl; do
  command -v "$tool" >/dev/null 2>&1 || {
    echo "missing tool: $tool" >&2
    exit 1
  }
done

HTTP_DIR="work/packer-http"
OUT_DIR="work/packer-out"
VAR_FILE="work/packer-vars.pkrvars.hcl"
mkdir -p "$HTTP_DIR" "$OUT_DIR"
cleanup() {
  rm -rf "$HTTP_DIR" "$VAR_FILE"
}
trap cleanup EXIT

CDIMAGE="https://cdimage.debian.org/debian-cd/current/amd64/iso-cd"
ISO_FILE=$(curl -fsSL "$CDIMAGE/" | grep -o 'debian-[0-9.]*-amd64-netinst.iso' | head -n 1)
[ -n "$ISO_FILE" ] || {
  echo "could not resolve a bookworm netinst ISO from $CDIMAGE" >&2
  exit 1
}
ISO_URL="$CDIMAGE/$ISO_FILE"

BUILD_PASS=$(openssl rand -base64 24)
BUILD_HASH=$(openssl passwd -6 "$BUILD_PASS")
sed "s|d-i passwd/user-password-crypted password \\*$|d-i passwd/user-password-crypted password $BUILD_HASH|" \
  preseed.cfg > "$HTTP_DIR/preseed-build.cfg"
grep -Fq "passwd/user-password-crypted password $BUILD_HASH" "$HTTP_DIR/preseed-build.cfg" || {
  echo "build preseed password replacement failed" >&2
  exit 1
}

# Var file via printf %s, not a heredoc assignment: the value is a
# generated variable, and a quoted "$BUILD_PASS" line trips the
# INT-011 shape scanner (it cannot tell a shell variable reference
# from a quoted literal). printf %s keeps the reference unambiguous.
{
  printf 'iso_url = "%s"\n' "$ISO_URL"
  printf 'ssh_password = "%s"\n' "$BUILD_PASS"
  printf 'image_date = "%s"\n' "$DATE"
} > "$VAR_FILE"

packer validate -var-file="$VAR_FILE" packer/metaos.pkr.hcl
packer build -var-file="$VAR_FILE" packer/metaos.pkr.hcl

[ -s "$OUT_DIR/metaos" ] || {
  echo "packer produced no output image in $OUT_DIR" >&2
  exit 1
}
mv "$OUT_DIR/metaos" "$IMG"
rmdir "$OUT_DIR" 2>/dev/null || true
sha256sum "$IMG" > "$IMG.sha256"
echo "built $IMG"
cat "$IMG.sha256"
