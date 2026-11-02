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
# face-site: repo-root product pages for dock iframes (served on 18934
# from /opt/face-site; unit in os-build/face/provision.sh). Same pull,
# same log. Boards data only: os/worlds is ~100M, the pages fetch just
# pack.json + officina runs + custos runs. http.server reads from disk
# per request, so no service restart is needed after this copy.
SITE_DST=/opt/face-site
mkdir -p "$SITE_DST"
for f in index.html surfaces.html logo-studio.html bus.html styles.css manifest.webmanifest icon-180.png; do
  if git --git-dir="$MIRROR" --work-tree="$WORK" checkout -q -f "$BRANCH" -- "$f" 2>/dev/null; then
    cp -f "$WORK/$f" "$SITE_DST/$f"
  else
    log "site: $f not in $BRANCH, keeping previous copy"
  fi
done
for d in js vendor design; do
  if git --git-dir="$MIRROR" --work-tree="$WORK" checkout -q -f "$BRANCH" -- "$d" 2>/dev/null; then
    rm -rf "$SITE_DST/$d"
    cp -r "$WORK/$d" "$SITE_DST/$d"
  else
    log "site: $d not in $BRANCH, keeping previous copy"
  fi
done
rm -rf "$SITE_DST/os"
for p in os/worlds/custos/pack.json os/worlds/dep/pack.json os/worlds/doe/pack.json os/worlds/dsny/pack.json os/worlds/ems/pack.json os/worlds/fdny/pack.json os/worlds/hospital/pack.json os/worlds/mta/pack.json os/worlds/nypd/pack.json os/worlds/officina/pack.json os/worlds/custos/runs os/worlds/officina/runs; do
  git --git-dir="$MIRROR" --work-tree="$WORK" checkout -q -f "$BRANCH" -- "$p" 2>/dev/null || log "site: $p not in $BRANCH, skipped"
done
if [ -d "$WORK/os/worlds" ]; then
  mkdir -p "$SITE_DST/os"
  cp -r "$WORK/os/worlds" "$SITE_DST/os/worlds"
fi
rm -rf "$WORK"
log "applied site updates $BEFORE -> $AFTER"
log "applied face updates $BEFORE -> $AFTER"
