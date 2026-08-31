#!/bin/bash

# Proves the explicit local-checkout synchronization route in a disposable
# guest. Nothing in this scenario runs against the daily host desktop.

omarchy_host_test() {
  local product_root source_dir plugin_dir first_commit second_commit installed_commit
  product_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
  source_dir="/tmp/omarchy-news-radar-local-latest"
  # The literal is expanded only by the disposable guest's shell.
  # shellcheck disable=SC2016
  plugin_dir='$HOME/.config/omarchy/plugins/io.github.mtolhuys.news-radar'

  log "Staging a clean local News Radar checkout"
  tar -C "$product_root" --exclude=.git --exclude=dist --exclude='__pycache__' -cf - . | ssh_guest \
    "mkdir -p '$source_dir' && tar -C '$source_dir' -xf -"
  ssh_guest "git -C '$source_dir' init -q && git -C '$source_dir' add . && \
    git -C '$source_dir' -c user.name=PluginLab -c user.email=lab@invalid commit -qm candidate"
  first_commit="$(ssh_guest "git -C '$source_dir' rev-parse HEAD")" || return 1

  log "Installing the exact clean checkout through make local-latest"
  ssh_session "cd '$source_dir' && make local-latest" >"$RUN_DIR/news-radar-local-latest-install.log" || return 1
  wait_for_guest_state "local-latest installs and enables the exact source commit" 20 ssh_session \
    "test \"\$(git -C $plugin_dir rev-parse HEAD)\" = '$first_commit' && \
     test \"\$(realpath -e -- \"\$(git -C $plugin_dir remote get-url origin)\")\" = '$source_dir' && \
     omarchy-plugin-list --json | jq -e 'any(.[]; .id == \"io.github.mtolhuys.news-radar\" and .enabled == true)'" || return 1

  log "Fast-forwarding the installed clone to the next committed source revision"
  ssh_guest "printf '\nLocal latest lifecycle fixture.\n' >>'$source_dir/CHANGELOG.md' && \
    git -C '$source_dir' add CHANGELOG.md && \
    git -C '$source_dir' -c user.name=PluginLab -c user.email=lab@invalid commit -qm next"
  second_commit="$(ssh_guest "git -C '$source_dir' rev-parse HEAD")" || return 1
  [[ $first_commit != "$second_commit" ]] || return 1
  ssh_session "cd '$source_dir' && make local-latest" >"$RUN_DIR/news-radar-local-latest-update.log" || return 1
  installed_commit="$(ssh_session "git -C $plugin_dir rev-parse HEAD")" || return 1
  [[ $installed_commit == "$second_commit" ]] || return 1
  ssh_session "cd '$source_dir' && make local-latest" >"$RUN_DIR/news-radar-local-latest-idempotent.log" || return 1
  grep -Fq 'is up to date.' "$RUN_DIR/news-radar-local-latest-idempotent.log" || return 1

  log "Refusing dirty source without disturbing the installed revision"
  ssh_guest "printf '\nUncommitted fixture.\n' >>'$source_dir/CHANGELOG.md'"
  if ssh_session "cd '$source_dir' && make local-latest" >"$RUN_DIR/news-radar-local-latest-dirty.log" 2>&1; then
    echo "local-latest accepted an uncommitted source tree" >&2
    return 1
  fi
  grep -Fq 'source checkout has uncommitted changes' "$RUN_DIR/news-radar-local-latest-dirty.log" || return 1
  [[ $(ssh_session "git -C $plugin_dir rev-parse HEAD") == "$second_commit" ]] || return 1

  ssh_session "omarchy-plugin-remove io.github.mtolhuys.news-radar --yes" >/dev/null || return 1
  wait_for_guest_state "local-latest installation removes cleanly" 15 ssh_session \
    "test ! -e $plugin_dir && omarchy-plugin-list --json | jq -e 'all(.[]; .id != \"io.github.mtolhuys.news-radar\")'" || return 1
  capture_console "success-news-radar-local-latest-removed"
  printf 'ok - make local-latest passed install, exact revision, update, idempotence, refusal, and removal assertions\n'
}
