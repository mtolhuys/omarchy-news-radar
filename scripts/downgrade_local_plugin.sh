#!/bin/bash

# Move the installed Omarchy News Radar plugin checkout to an older revision
# so the in-panel Update control can be exercised safely.
#
# Usage:
#   make local-downgrade              # one commit behind current HEAD
#   make local-downgrade N=3          # three commits behind current HEAD
#   make local-downgrade REF=v0.4.14  # exact tag / commit / ref

set -euo pipefail

PLUGIN_ID="io.github.mtolhuys.news-radar"
N="${N:-1}"
REF="${REF:-}"

fail() {
  echo "news-radar local-downgrade: $*" >&2
  exit 1
}

for command in git omarchy-plugin-validate omarchy-shell; do
  command -v "$command" >/dev/null 2>&1 || fail "required command is unavailable: $command"
done

[[ ${HOME:-} == /* && $HOME != / ]] || fail "HOME must be an absolute non-root user directory"
[[ "$N" =~ ^[1-9][0-9]*$ ]] || fail "N must be a positive integer (got: $N)"

TARGET="$HOME/.config/omarchy/plugins/$PLUGIN_ID"
[[ -d $TARGET/.git ]] || fail "installed plugin is not a Git checkout: $TARGET"
[[ ! -L $TARGET ]] || fail "installed plugin path is a symlink; refusing to follow it: $TARGET"

if [[ -n $(git -C "$TARGET" status --porcelain --untracked-files=normal) ]]; then
  fail "installed plugin has local changes; commit, stash, or sync before downgrading"
fi

BEFORE=$(git -C "$TARGET" rev-parse --verify HEAD)

if [[ -n $REF ]]; then
  TARGET_COMMIT=$(git -C "$TARGET" rev-parse --verify "$REF^{commit}") ||
    fail "REF is not a known commit in the installed checkout: $REF"
else
  TARGET_COMMIT=$(git -C "$TARGET" rev-parse --verify "HEAD~${N}") ||
    fail "cannot walk back $N commit(s) from $BEFORE"
fi

if [[ $TARGET_COMMIT == "$BEFORE" ]]; then
  echo "Installed plugin is already at $BEFORE."
  exit 0
fi

# Ensure the older tree still validates as an Omarchy plugin before we keep it.
WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT
git -C "$TARGET" archive --format=tar "$TARGET_COMMIT" | tar -C "$WORKDIR" -xf -
omarchy-plugin-validate "$WORKDIR" ||
  fail "target revision $TARGET_COMMIT failed omarchy-plugin-validate; leaving installed checkout at $BEFORE"

git -C "$TARGET" reset --hard "$TARGET_COMMIT" >/dev/null
AFTER=$(git -C "$TARGET" rev-parse --verify HEAD)
[[ $AFTER == "$TARGET_COMMIT" ]] || fail "reset did not land on $TARGET_COMMIT"

# Reload shell plugin generations so the panel matches the downgraded tree.
omarchy-shell shell rescanPlugins >/dev/null 2>&1 ||
  fail "downgraded to $AFTER but omarchy-shell rescanPlugins failed"

SUBJECT=$(git -C "$TARGET" log -1 --pretty=%s "$AFTER")
echo "Downgraded $PLUGIN_ID"
echo "  from $BEFORE"
echo "  to   $AFTER ($SUBJECT)"
echo "Reopen News Radar to exercise the Update control, then make local-latest to return to tip."
