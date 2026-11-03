#!/bin/sh
# Deploy the Meta Trio static demo frontend to Cloudflare.
# Pinned command for Del / any operator with wrangler auth.
# Publishes ONLY the static demo files; server/ stays local (it needs keys).
#
# Usage:  sh os/docs/deploy-trio-frontend.sh
# Needs:  wrangler authenticated (wrangler login) — no token in this file, ever.
#
# What it publishes (repo-root demo set):
#   index.html  styles.css  manifest.webmanifest  icon-180.png
#   surfaces.html  logo-studio.html  design/meta-ascii-logo-studio.html
#   js/  vendor/maplibre/
# Deliberately excluded: server/ (needs SPARK_API_KEY in env, never shipped),
#   bus.html (Rowan's dashboard viewer lane), native/, crates/, tests, docs.
#
# On a static host there is no /api/assess backend, so the UI shows its
# honest "Model backend not connected" state until the endpoint field is
# pointed at a live server (see os-build/RUNBOOK.md step 3). That is by
# design, not a deploy failure.
set -eu
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DIST="$ROOT/.pages-trio-dist"
PROJECT="meta-trio-demo"

rm -rf "$DIST"
mkdir -p "$DIST/design" "$DIST/vendor/maplibre"
cp "$ROOT/index.html" "$ROOT/styles.css" "$ROOT/manifest.webmanifest" \
   "$ROOT/icon-180.png" "$ROOT/surfaces.html" "$ROOT/logo-studio.html" "$DIST/"
cp -r "$ROOT/js" "$DIST/js"
cp "$ROOT/vendor/maplibre/maplibre-gl.js" "$ROOT/vendor/maplibre/maplibre-gl.css" \
   "$DIST/vendor/maplibre/"
cp "$ROOT/design/meta-ascii-logo-studio.html" "$DIST/design/"

# Fail closed on accidental secrets in the public set.
if grep -riE 'SPARK_API_KEY|CLOUDFLARE_API_TOKEN|sk-(ant|live)' "$DIST" >/dev/null; then
  echo "REFUSING: possible secret in dist set" >&2
  exit 1
fi

wrangler pages deploy "$DIST" --project-name="$PROJECT"
echo "Verify: curl -s https://meta-trio-demo.openlane.workers.dev/ | grep -F '<title>Meta Imperium'"
echo "Then log deployment id + URL in os/docs/DEPLOY_RUNBOOK.md section 6."
