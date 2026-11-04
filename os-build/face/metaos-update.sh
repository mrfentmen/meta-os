#!/bin/sh
# metaos-update: passive updater (face task 12). Pulls the OS repo,
# applies face updates (os-build/face -> /opt/face), logs every run.
# STOP file /etc/metaos/STOP disables pulls (still logs the skip).
# No secrets: public https clone only.
set -eu
REPO_URL="${METAOS_REPO_URL:-https://github.com/mrfentmen/meta-os.git}"
BRANCH="${METAOS_BRANCH:-main}"
MIRROR="${METAOS_MIRROR:-/var/lib/metaos/repo.git}"
LOG="${METAOS_LOG:-/var/log/metaos-update.log}"
STOP="${METAOS_STOP:-/etc/metaos/STOP}"
FACE_DST="${METAOS_FACE_DST:-/opt/face}"
CHECK_SITE=0
for a in "$@"; do
  case "$a" in
    --check-site) CHECK_SITE=1 ;;
  esac
done
log() { printf '%s metaos-update: %s\n' "$(date -u +%FT%TZ)" "$*" | tee -a "$LOG"; }
SITE_DST="${SITE_DST:-/opt/face-site}"
# --check-site is read-only and runs before any setup that needs root, so it
# works from a login session as well as from the update service.
if [ "$CHECK_SITE" = 1 ]; then
  fails=0; total=0
  check_site() { # check_site <relative path>
    total=$((total + 1))
    if [ -e "$SITE_DST/$1" ]; then
      if [ -d "$SITE_DST/$1" ]; then
        echo "check-site ok: $1 ($(du -sk "$SITE_DST/$1" | cut -f1) KB)"
      else
        echo "check-site ok: $1 ($(wc -c <"$SITE_DST/$1" | tr -d ' ') bytes)"
      fi
    else
      echo "check-site MISSING: $1"
      fails=$((fails + 1))
    fi
  }
  for f in index.html surfaces.html logo-studio.html bus.html styles.css manifest.webmanifest icon-180.png; do
    check_site "$f"
  done
  for f in labs/molecules/index.html labs/music3d/index.html labs/science-lab-review/index.html \
           aegis/index.html \
           design/agent-budget-dashboard.html design/meta-musica-notes.html \
           design/meta-custos-watch.html design/meta-officina-blueprint.html \
           js/app.js; do
    check_site "$f"
  done
  for p in os/worlds/nypd/pack.json os/worlds/fdny/pack.json os/worlds/ems/pack.json \
           os/worlds/mta/pack.json os/worlds/dep/pack.json os/worlds/doe/pack.json \
           os/worlds/dsny/pack.json os/worlds/hospital/pack.json \
           os/worlds/custos/pack.json os/worlds/officina/pack.json \
           os/worlds/musica/sessions/hn029-chipsynth/normalized/take-006.wav; do
    check_site "$p"
  done
  echo "check-site: $((total - fails))/$total present at $SITE_DST"
  [ "$fails" -eq 0 ] || exit 1
  exit 0
fi
mkdir -p "$(dirname "$STOP")" "$(dirname "$MIRROR")" "$(dirname "$LOG")" "$FACE_DST"
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
cp -r "$WORK/os-build/face/." "$FACE_DST/"
# face-site: repo-root product pages for dock iframes (served on 18934
# from /opt/face-site; unit in os-build/face/provision.sh). Same pull,
# same log. Boards data only: os/worlds is ~100M, the pages fetch just
# pack.json + officina runs + custos runs. http.server reads from disk
# per request, so no service restart is needed after this copy.
mkdir -p "$SITE_DST"
for f in index.html surfaces.html logo-studio.html bus.html styles.css manifest.webmanifest icon-180.png; do
  if git --git-dir="$MIRROR" --work-tree="$WORK" checkout -q -f "$BRANCH" -- "$f" 2>/dev/null; then
    cp -f "$WORK/$f" "$SITE_DST/$f"
    log "site: $f ($(wc -c <"$SITE_DST/$f" | tr -d ' ') bytes)"
  else
    log "site: $f not in $BRANCH, keeping previous copy"
  fi
done
# Imperium's console links ../styles.css and ../vendor, so the site root is the
# only place its page is styled. Keep a copy here for the Trio/Imperium tiles.
if git --git-dir="$MIRROR" --work-tree="$WORK" checkout -q -f "$BRANCH" -- imperium 2>/dev/null; then
  rm -rf "$SITE_DST/imperium"
  cp -r "$WORK/imperium" "$SITE_DST/imperium"
  log "site: imperium ($(wc -c <"$SITE_DST/imperium/index.html" | tr -d ' ') bytes)"
else
  log "site: imperium not in $BRANCH, keeping previous copy"
fi
for lab in molecules music3d science-lab-review; do
  git --git-dir="$MIRROR" --work-tree="$WORK" checkout -q -f "$BRANCH" -- "labs/$lab" 2>/dev/null || log "site: labs/$lab not in $BRANCH, skipped"
done
if [ -d "$WORK/labs" ]; then
  mkdir -p "$SITE_DST/labs"
  for lab in molecules music3d science-lab-review; do
    if [ -d "$WORK/labs/$lab" ]; then
      rm -rf "$SITE_DST/labs/$lab"
      cp -r "$WORK/labs/$lab" "$SITE_DST/labs/$lab"
      log "site: labs/$lab ($(du -sk "$SITE_DST/labs/$lab" | cut -f1) KB)"
    fi
  done
fi
# Aegis security page (agent-3's directory). Missing until they land it: log
# and keep the previous copy, never fail the run over it.
if git --git-dir="$MIRROR" --work-tree="$WORK" checkout -q -f "$BRANCH" -- "aegis-page" 2>/dev/null; then
  rm -rf "$SITE_DST/aegis"
  mkdir -p "$SITE_DST/aegis"
  cp -r "$WORK/aegis-page/." "$SITE_DST/aegis/"
  log "site: aegis ($(du -sk "$SITE_DST/aegis" | cut -f1) KB)"
else
  log "site: aegis-page not in $BRANCH, keeping previous copy"
fi
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
git --git-dir="$MIRROR" --work-tree="$WORK" checkout -q -f "$BRANCH" -- "os/worlds/musica/sessions/hn029-chipsynth/normalized/take-006.wav" 2>/dev/null || log "site: take-006.wav not in $BRANCH, skipped"
if [ -d "$WORK/os/worlds" ]; then
  mkdir -p "$SITE_DST/os"
  cp -r "$WORK/os/worlds" "$SITE_DST/os/worlds"
fi
rm -rf "$WORK"
log "applied site updates $BEFORE -> $AFTER"
log "applied face updates $BEFORE -> $AFTER"
