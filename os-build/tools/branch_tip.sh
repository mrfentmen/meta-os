#!/usr/bin/env bash
# CB-076 — print branch, tip sha and files changed vs main.
set -euo pipefail

REPO="${1:-$(git rev-parse --show-toplevel)}"
cd "$REPO"
BASE="${BASE:-main}"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
TIP="$(git rev-parse HEAD)"

printf 'repo: %s\n' "$(git rev-parse --show-toplevel)"
printf 'branch: %s\n' "$BRANCH"
printf 'tip: %s\n' "$TIP"
if ! git rev-parse --verify --quiet "$BASE" >/dev/null; then
  printf 'base: %s (missing)\n' "$BASE" >&2
  exit 1
fi
printf 'base: %s\n' "$BASE"
printf 'changed vs %s:\n' "$BASE"
git diff --name-only "$BASE"...HEAD
