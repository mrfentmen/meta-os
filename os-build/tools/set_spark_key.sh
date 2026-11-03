#!/bin/sh
# set_spark_key.sh — put the hackathon model key into the OS image, once, safely.
#
# The image ships /etc/metaos/agent.env with EMPTY values on purpose: a key in a
# repo or in a built image is a leaked key. This tool fills that one file on a
# local image, root-owned 0600, and proves the write by comparing a SHA-256 of
# the value on both sides. It never prints the key and never puts it on a
# command line (stdin only, so it is not in `ps`).
#
#   sh os-build/tools/set_spark_key.sh                       # /tmp/metaos.ext4
#   sh os-build/tools/set_spark_key.sh --image /path.img --key "/path/Hackathon Key.txt"
#   sh os-build/tools/set_spark_key.sh --check               # is a key present?
#
# macOS cannot mount ext4, so the write happens inside a throwaway ubuntu
# container with the image loop-mounted. Exit 1 on any doubt.
set -eu

IMAGE=/tmp/metaos.ext4
KEYFILE="$HOME/Desktop/Hackathon Key.txt"
MODE=write
while [ $# -gt 0 ]; do
  case "$1" in
    --image) IMAGE="$2"; shift 2 ;;
    --key) KEYFILE="$2"; shift 2 ;;
    --check) MODE=check; shift ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    *) echo "set_spark_key: unknown argument $1" >&2; exit 2 ;;
  esac
done

[ -f "$IMAGE" ] || { echo "set_spark_key: no image at $IMAGE" >&2; exit 1; }
if pgrep -f "qemu-system.*$(basename "$IMAGE")" >/dev/null 2>&1; then
  echo "set_spark_key: $IMAGE is booted right now; shut the VM down first" >&2
  exit 1
fi

run_in_image() {
  # $1 = container script; stdin passes through
  # -c, not -lc: a login shell under `set -eu` dies silently before the script
  # body, which cost a debugging round and could hide a failed write.
  docker run --rm --privileged -i -v "$IMAGE:/disk.img" \
    -e EXPECT_SHA="${EXPECT_SHA:-}" ubuntu:24.04 bash -c "$1"
}

if [ "$MODE" = check ]; then
  run_in_image '
    set -eu
    mkdir -p /mnt
    mount -o loop /disk.img /mnt
    f=/mnt/etc/metaos/agent.env
    if [ ! -f "$f" ]; then echo "check: no $f"; umount /mnt; exit 1; fi
    n=$(grep -cE "^SPARK_API_KEY=.{20,}" "$f" || true)
    st=$(stat -c "%a %U" "$f")
    umount /mnt
    echo "check: key-present=$n mode-owner=$st"
    [ "$n" = 1 ]
  '
  exit $?
fi

[ -f "$KEYFILE" ] || { echo "set_spark_key: no key file at $KEYFILE" >&2; exit 1; }
KEY="$(tr -d '\r\n' < "$KEYFILE")"
[ -n "$KEY" ] || { echo "set_spark_key: key file is empty" >&2; exit 1; }
[ "${#KEY}" -ge 24 ] || { echo "set_spark_key: key is too short to be real" >&2; exit 1; }

EXPECT_SHA="$(printf '%s' "$KEY" | shasum -a 256 | awk '{print $1}')"
export EXPECT_SHA

printf '%s' "$KEY" | run_in_image '
  set -eu
  umask 077
  # Plain read: `IFS= read` followed by set -e exits on the temporary-assignment
  # form and would look like an empty key. Trim after reading instead.
  read -r KEY || true
  KEY=$(printf %s "$KEY" | tr -d "[:space:]")
  [ -n "$KEY" ] || { echo "set_spark_key: no key on stdin" >&2; exit 1; }
  mkdir -p /mnt
  mount -o loop /disk.img /mnt
  trap "umount /mnt 2>/dev/null || true" EXIT
  d=/mnt/etc/metaos
  mkdir -p "$d"
  {
    echo "# /etc/metaos/agent.env — machine secrets for the Meta agent layer."
    echo "# Filled on this image by os-build/tools/set_spark_key.sh. Root 0600."
    echo "# The login hook sources this file and imports non-empty values into the"
    echo "# user manager; nothing here is ever written to a repo."
    echo "#   SPARK_API_KEY: direct Meta model transport (agents/model_client.mjs,"
    echo "#                  server/queue/spark_gen.py). Empty = the agent refuses."
    echo "#   METAOS_NOTIFY_WEBHOOK: optional relay webhook. Empty = journal only."
    printf "SPARK_API_KEY=%s\n" "$KEY"
    printf "METAOS_NOTIFY_WEBHOOK=\n"
  } > "$d/agent.env"
  chmod 0600 "$d/agent.env"
  chown 0:0 "$d/agent.env" 2>/dev/null || true

  # Prove the write without printing it: same value, same hash, right mode.
  # No trailing newline in the hash: the host hashes the value alone.
  got=$(printf %s "$(sed -n "s/^SPARK_API_KEY=//p" "$d/agent.env")" | sha256sum | awk "{print \$1}")
  mode=$(stat -c "%a" "$d/agent.env")
  lines=$(grep -c "^SPARK_API_KEY=." "$d/agent.env" || true)
  umount /mnt
  trap - EXIT
  echo "installed: lines=$lines mode=$mode sha-match=$([ "$got" = "$EXPECT_SHA" ] && echo yes || echo NO)"
  [ "$lines" = 1 ] && [ "$mode" = 600 ] && [ "$got" = "$EXPECT_SHA" ]
'

echo "set_spark_key: done. In the guest, the login hook imports it at login;"
echo "verify with:  meta-ask --list   then   node /usr/share/metaos/agent/agents/agent_loop.mjs --task 'say hello'"
