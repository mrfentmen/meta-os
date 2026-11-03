#!/bin/sh
# make-seed.sh — rebuild the OC2 NoCloud seed ISO (byte-identical recipe).
# Usage: sh agent-layer/make-seed.sh [output.iso] [instance-id]
# Re-runnable; overwrites only its own outputs. macOS (hdiutil) and Linux
# (genisoimage/xorrisofs) supported. No secrets: keypair is relay login key.
set -u
OUT="${1:-/Users/test/.opencode/scratch/oc2-seed.iso}"
INSTANCE_ID="${2:-metaos-oc2b-$(date +%Y%m%d)}"
KEY="$HOME/.ssh/oc2_accept"
WORK="$(mktemp -d)"

if [ ! -f "$KEY" ]; then
  ssh-keygen -t ed25519 -f "$KEY" -N "" -C "oc2-seed" >/dev/null
  echo "generated $KEY(.pub)"
fi
mkdir -p "$WORK/seed"
cp "$KEY.pub" "$WORK/seed/authorized_key" 2>/dev/null || true
cat > "$WORK/seed/meta-data" <<EOF
instance-id: $INSTANCE_ID
local-hostname: metaos
EOF
PUBKEY="$(cat "$KEY.pub")"
cat > "$WORK/seed/user-data" <<EOF
#cloud-config
users:
  - name: relay
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh_authorized_keys:
      - $PUBKEY
EOF
if command -v hdiutil >/dev/null 2>&1; then
  hdiutil makehybrid -iso -joliet -iso-volume-name CIDATA \
    -joliet-volume-name CIDATA -o "$OUT" "$WORK/seed" >/dev/null
elif command -v genisoimage >/dev/null 2>&1; then
  genisoimage -output "$OUT" -volid CIDATA -joliet -rock "$WORK/seed" >/dev/null 2>&1
elif command -v xorrisofs >/dev/null 2>&1; then
  xorrisofs -o "$OUT" -V CIDATA -J -r "$WORK/seed" >/dev/null 2>&1
else
  echo "FAIL: no ISO tool (hdiutil/genisoimage/xorrisofs)" >&2; exit 1
fi
rm -rf "$WORK"
ls -la "$OUT" | awk '{print "seed:", $9, $5, "bytes"}'
echo "instance-id: $INSTANCE_ID"
