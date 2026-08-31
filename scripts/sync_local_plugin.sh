#!/bin/bash

# Explicitly install or fast-forward the local Omarchy plugin clone to this
# repository's current committed HEAD. This intentionally does not pull the
# source checkout, install the optional shortcut, or overwrite another origin.

set -euo pipefail

PLUGIN_ID="io.github.mtolhuys.news-radar"
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
SOURCE_ROOT=$(git -C "$SCRIPT_DIR/.." rev-parse --show-toplevel)
SOURCE_ROOT=$(realpath -e -- "$SOURCE_ROOT")

fail() {
  echo "news-radar local-latest: $*" >&2
  exit 1
}

for command in git jq omarchy-plugin-add omarchy-plugin-update omarchy-plugin-validate; do
  command -v "$command" >/dev/null 2>&1 || fail "required command is unavailable: $command"
done

[[ ${HOME:-} == /* && $HOME != / ]] || fail "HOME must be an absolute non-root user directory"
[[ $(jq -r '.id // empty' "$SOURCE_ROOT/manifest.json") == "$PLUGIN_ID" ]] ||
  fail "source manifest identity does not match $PLUGIN_ID"

if [[ -n $(git -C "$SOURCE_ROOT" status --porcelain --untracked-files=normal) ]]; then
  fail "source checkout has uncommitted changes; commit or stash them before syncing"
fi

omarchy-plugin-validate "$SOURCE_ROOT"

SOURCE_COMMIT=$(git -C "$SOURCE_ROOT" rev-parse --verify HEAD)
TARGET="$HOME/.config/omarchy/plugins/$PLUGIN_ID"

if [[ ! -e $TARGET && ! -L $TARGET ]]; then
  omarchy-plugin-add "$SOURCE_ROOT" --enable --yes
elif [[ -L $TARGET ]]; then
  fail "installed plugin path is a symlink; refusing to replace or follow it: $TARGET"
elif [[ ! -d $TARGET/.git ]]; then
  fail "installed plugin is not a Git checkout; refusing to replace it: $TARGET"
else
  if [[ -n $(git -C "$TARGET" status --porcelain --untracked-files=normal) ]]; then
    fail "installed plugin has local changes; refusing to overwrite them: $TARGET"
  fi
  ORIGIN=$(git -C "$TARGET" remote get-url origin 2>/dev/null) ||
    fail "installed plugin has no readable origin"
  case "$ORIGIN" in
    file://*) ORIGIN_PATH=${ORIGIN#file://} ;;
    /*) ORIGIN_PATH=$ORIGIN ;;
    *) fail "installed plugin tracks a non-local origin; refusing to repoint it: $ORIGIN" ;;
  esac
  ORIGIN_ROOT=$(realpath -e -- "$ORIGIN_PATH") || fail "installed plugin origin no longer exists: $ORIGIN_PATH"
  [[ $ORIGIN_ROOT == "$SOURCE_ROOT" ]] ||
    fail "installed plugin tracks a different local checkout; refusing to repoint it: $ORIGIN_ROOT"
  omarchy-plugin-update "$PLUGIN_ID" --yes
fi

[[ ! -L $TARGET && -d $TARGET/.git ]] || fail "Omarchy did not create a Git-managed plugin checkout"
INSTALLED_COMMIT=$(git -C "$TARGET" rev-parse --verify HEAD)
[[ $INSTALLED_COMMIT == "$SOURCE_COMMIT" ]] ||
  fail "installed revision $INSTALLED_COMMIT does not match source revision $SOURCE_COMMIT"
[[ -z $(git -C "$TARGET" status --porcelain --untracked-files=normal) ]] ||
  fail "installed plugin is not clean after synchronization"

printf 'News Radar local plugin is current at %s.\n' "$SOURCE_COMMIT"
printf 'Rerun make local-latest after each committed source change.\n'
