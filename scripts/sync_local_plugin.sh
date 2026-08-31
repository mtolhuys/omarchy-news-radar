#!/bin/bash

# Explicitly install or fast-forward the local Omarchy plugin clone to this
# repository's current committed HEAD, then build and import one real local
# edition. This intentionally does not pull the source checkout, install the
# optional shortcut, or overwrite another origin.

set -euo pipefail

PLUGIN_ID="io.github.mtolhuys.news-radar"
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
SOURCE_ROOT=$(git -C "$SCRIPT_DIR/.." rev-parse --show-toplevel)
SOURCE_ROOT=$(realpath -e -- "$SOURCE_ROOT")

fail() {
  echo "news-radar local-latest: $*" >&2
  exit 1
}

for command in cp find git jq mktemp omarchy-plugin-add omarchy-plugin-disable omarchy-plugin-enable \
  omarchy-plugin-update omarchy-plugin-validate python3 realpath; do
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

# The early panel-only preview was stored in plugins[]. Omarchy correctly
# stores the paired panel/bar-widget in bar.layout.*, but updating a manifest
# cannot infer that one-time location migration. Move only the exact unmodified
# owned entry through Omarchy's lifecycle; every other shape fails closed.
SHELL_CONFIG="$HOME/.config/omarchy/shell.json"
if [[ -f $SHELL_CONFIG ]]; then
  LEGACY_COUNT=$(jq -r --arg id "$PLUGIN_ID" \
    '[.plugins[]? | select((if type == "object" then .id else . end) == $id)] | length' \
    "$SHELL_CONFIG") || fail "cannot inspect Omarchy shell configuration"
  BAR_COUNT=$(jq -r --arg id "$PLUGIN_ID" \
    '[.bar.layout.left[]?, .bar.layout.center[]?, .bar.layout.right[]? | select((if type == "object" then .id else . end) == $id)] | length' \
    "$SHELL_CONFIG") || fail "cannot inspect Omarchy bar configuration"
  if (( LEGACY_COUNT > 0 && BAR_COUNT > 0 )); then
    fail "plugin has ambiguous legacy and bar placements; refusing to change shell configuration"
  elif (( LEGACY_COUNT > 1 )); then
    fail "plugin has multiple legacy placements; refusing to change shell configuration"
  elif (( LEGACY_COUNT == 1 )); then
    jq -e --arg id "$PLUGIN_ID" \
      'any(.plugins[]?; type == "object" and .id == $id and (keys | sort) == ["id"])' \
      "$SHELL_CONFIG" >/dev/null ||
      fail "legacy plugin placement has custom fields; refusing to replace it"
    omarchy-plugin-disable "$PLUGIN_ID"
    omarchy-plugin-enable "$PLUGIN_ID" --section right
    "$TARGET/bin/news-radar-client" set-preferences --bar-visible true --images-visible true >/dev/null
    printf 'Migrated the panel-only preview to the default-on right-side newspaper.\n'
  fi
fi

WORK_DIR=$(mktemp -d)
cleanup() {
  [[ -n ${WORK_DIR:-} && -d $WORK_DIR ]] && find "$WORK_DIR" -depth -delete
}
trap cleanup EXIT

if [[ ${OMARCHY_NEWS_RADAR_TEST_MODE:-} == 1 && -n ${OMARCHY_NEWS_RADAR_TEST_EDITION:-} ]]; then
  EDITION=$(realpath -e -- "$OMARCHY_NEWS_RADAR_TEST_EDITION") ||
    fail "test edition directory does not exist"
else
  cp -- "$SOURCE_ROOT/state/source-snapshot.json" "$WORK_DIR/source-snapshot.json"
  EDITION="$WORK_DIR/edition"
  PYTHONPATH="$SOURCE_ROOT" SOURCE_REVISION="$SOURCE_COMMIT" \
    python3 -B -m radar collect --snapshot "$WORK_DIR/source-snapshot.json" --output "$EDITION"
fi

IMPORT_RESULT=$(PYTHONPATH="$SOURCE_ROOT" python3 -B -m radar import-local-edition --edition "$EDITION") ||
  fail "real local edition could not be imported; the prior cache was preserved"
[[ $(jq -r '.sourceRevision // empty' <<<"$IMPORT_RESULT") == "$SOURCE_COMMIT" ]] ||
  fail "local edition revision does not match the synchronized source commit"

printf 'News Radar local plugin is current at %s.\n' "$SOURCE_COMMIT"
printf 'Imported %s real stories with %s validated images from the live sources.\n' \
  "$(jq -r '.events' <<<"$IMPORT_RESULT")" "$(jq -r '.images' <<<"$IMPORT_RESULT")"
printf 'Rerun make local-latest whenever you want a newly collected local edition.\n'
