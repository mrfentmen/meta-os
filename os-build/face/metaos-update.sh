#!/bin/sh
# metaos-update: passive updater (face task 12). Pulls the OS repo,
# applies face updates (os-build/face -> /opt/face), logs every run.
# STOP file /etc/metaos/STOP disables pulls (still logs the skip).
# No secrets: public https clone only.
set -eu
REPO_URL="${METAOS_REPO_URL:-https://github.com/mrfentmen/meta-os.git}"
BRANCH="${METAOS_BRANCH:-main}"
MIRROR=/var/lib/metaos/repo.git
LOG=/var/log/metaos-update.log
STOP=/etc/metaos/STOP
log() { printf '%s metaos-update: %s\n' "$(date -u +%FT%TZ)" "$*" | tee -a "$LOG"; }
mkdir -p /etc/metaos /var/lib/metaos /opt/face
touch "$LOG"
if [ -f "$STOP" ]; then log "STOP present, skipping pull"; exit 0; fi
if [ ! -d "$MIRROR" ]; then
  log "cloning $REPO_URL ($BRANCH)"
  git clone -q --mirror --branch "$BRANCH" "$REPO_URL" "$MIRROR" || { log "clone FAILED"; exit 1; }
fi
BEFORE=$(git --git-dir="$MIRROR" rev-parse --short HEAD)
# NOTE: this is a --mirror clone, so remote branches land as local
# refs (refs/heads/*), not refs/remotes/origin/*. Fetch straight
# into the local branch ref.
git --git-dir="$MIRROR" fetch -q origin "+refs/heads/$BRANCH:refs/heads/$BRANCH" || { log "fetch FAILED"; exit 1; }
AFTER=$(git --git-dir="$MIRROR" rev-parse --short "$BRANCH")
if [ "$BEFORE" = "$AFTER" ]; then log "no changes ($AFTER)"; exit 0; fi
log "pulling $BEFORE -> $AFTER"
WORK=$(mktemp -d)
git --git-dir="$MIRROR" --work-tree="$WORK" checkout -q -f "$BRANCH" -- os-build/face || { log "checkout FAILED"; rm -rf "$WORK"; exit 1; }
cp -r "$WORK/os-build/face/." /opt/face/
rm -rf "$WORK"
log "applied face updates $BEFORE -> $AFTER"
