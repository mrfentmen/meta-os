#!/bin/sh
# install_agent_runtime.sh — copy the thinking agent into the image, then prove
# it runs with the image's own node and python (chroot, no boot).
#
# The image already carries /usr/share/metaos/agent (stage.sh puts it there).
# This tool refreshes the JS side after the repo changes and runs the agent's
# self-test inside the image, so "it ships" is a read-back, not a promise.
#
#   sh os-build/tools/install_agent_runtime.sh [--image /tmp/metaos.ext4]
set -eu

IMAGE=/tmp/metaos.ext4
while [ $# -gt 0 ]; do
  case "$1" in
    --image) IMAGE="$2"; shift 2 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "install_agent_runtime: unknown argument $1" >&2; exit 2 ;;
  esac
done
[ -f "$IMAGE" ] || { echo "install_agent_runtime: no image at $IMAGE" >&2; exit 1; }
if pgrep -f "qemu-system.*$(basename "$IMAGE")" >/dev/null 2>&1; then
  echo "install_agent_runtime: image is booted; stop the VM first" >&2
  exit 1
fi
REPO="$(cd "$(dirname "$0")/../.." && pwd)"

REPO="$REPO" docker run --rm --privileged -i \
  -v "$IMAGE:/disk.img" -v "$REPO:/repo:ro" ubuntu:24.04 bash -c '
  set -eu
  mkdir -p /mnt
  mount -o loop /disk.img /mnt
  trap "umount /mnt 2>/dev/null || true" EXIT
  D=/mnt/usr/share/metaos/agent
  mkdir -p "$D/agents"
  if [ ! -d "$D/server" ]; then
    echo "install_agent_runtime: $D/server is missing — run agent-layer/stage.sh first" >&2
    exit 1
  fi
  n=0
  for f in /repo/agents/*.mjs; do
    install -m644 "$f" "$D/agents/$(basename "$f")"
    n=$((n+1))
  done
  install -m644 /repo/agents/registry.json "$D/agents/registry.json"
  echo "installed: $n js files + registry.json into $D/agents"

  # Read back, then execute inside the image: node --version, registry check,
  # agent self-test (tools only, no model, no key needed).
  for f in agent_loop.mjs model_client.mjs runtime.mjs; do
    cmp -s "/repo/agents/$f" "$D/agents/$f" || { echo "MISMATCH $f" >&2; exit 1; }
    echo "match: $f"
  done
  mount --bind /dev /mnt/dev
  mount --bind /proc /mnt/proc
  mount --bind /sys /mnt/sys
  cp /etc/resolv.conf /mnt/etc/resolv.conf 2>/dev/null || true
  echo "--- image node"
  chroot /mnt /usr/bin/node --version
  echo "--- registry validate (image node, meta-coder present?)"
  chroot /mnt /usr/bin/node -e "
    const r = require(\"/usr/share/metaos/agent/agents/registry.json\");
    const a = r.agents.find(x => x.name === \"meta-coder\");
    if (!a) { console.error(\"no meta-coder\"); process.exit(1); }
    console.log(\"meta-coder live:\", a.command.join(\" \"), \"| maxActions\", a.budget.maxActions);
  "
  echo "--- agent self-test (image node)"
  chroot /mnt /usr/bin/node /usr/share/metaos/agent/agents/agent_loop.mjs --self-test
  echo "--- key present in image (length only)"
  chroot /mnt sh -c "test -f /etc/metaos/agent.env && stat -c \"agent.env mode=%a\" /etc/metaos/agent.env"
'
echo "install_agent_runtime: done"
