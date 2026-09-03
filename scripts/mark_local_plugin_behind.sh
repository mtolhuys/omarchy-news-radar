#!/bin/bash

# Leave the installed plugin where it is, and advance this source checkout by one
# empty commit so `origin HEAD` is ahead. Reopen Radar to see the Update notice
# without losing the Update UI that lives in the currently installed revision.
#
# Usage: make local-behind

set -euo pipefail

PLUGIN_ID="io.github.mtolhuys.news-radar"
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
SOURCE_ROOT=$(git -C "$SCRIPT_DIR/.." rev-parse --show-toplevel)
SOURCE_ROOT=$(realpath -e -- "$SOURCE_ROOT")

fail() {
  echo "news-radar local-behind: $*" >&2
  exit 1
}

command -v git >/dev/null 2>&1 || fail "required command is unavailable: git"
[[ -n $(git -C "$SOURCE_ROOT" status --porcelain --untracked-files=normal) ]] &&
  fail "source checkout has uncommitted changes; commit or stash them first"

TARGET="$HOME/.config/omarchy/plugins/$PLUGIN_ID"
[[ -d $TARGET/.git ]] || fail "installed plugin is not a Git checkout: $TARGET"

ORIGIN=$(git -C "$TARGET" remote get-url origin 2>/dev/null) ||
  fail "installed plugin has no readable origin"
case "$ORIGIN" in
  file://*) ORIGIN_PATH=${ORIGIN#file://} ;;
  /*) ORIGIN_PATH=$ORIGIN ;;
  *) fail "installed plugin does not track a local origin ($ORIGIN); use make local-latest first" ;;
esac
ORIGIN_ROOT=$(realpath -e -- "$ORIGIN_PATH") || fail "origin path missing: $ORIGIN_PATH"
[[ $ORIGIN_ROOT == "$SOURCE_ROOT" ]] ||
  fail "installed plugin origin is not this checkout ($ORIGIN_ROOT)"

BEFORE_INSTALL=$(git -C "$TARGET" rev-parse --verify HEAD)
BEFORE_SOURCE=$(git -C "$SOURCE_ROOT" rev-parse --verify HEAD)
[[ $BEFORE_INSTALL == "$BEFORE_SOURCE" ]] ||
  fail "installed revision differs from source HEAD; run make local-latest first (install=$BEFORE_INSTALL source=$BEFORE_SOURCE)"

git -C "$SOURCE_ROOT" commit --allow-empty -m "test: mark installed News Radar behind for update UI"
AFTER_SOURCE=$(git -C "$SOURCE_ROOT" rev-parse --verify HEAD)

echo "Source advanced to $AFTER_SOURCE"
echo "Installed plugin remains at $BEFORE_INSTALL"
echo "Reopen News Radar — Update plugin should appear. Click it, or run make local-latest."
