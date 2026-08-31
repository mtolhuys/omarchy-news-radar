#!/bin/bash

# Proves the explicit local-checkout synchronization route in a disposable
# guest. Nothing in this scenario runs against the daily host desktop.

omarchy_host_test() {
  local product_root source_dir edition_dir plugin_dir helper first_commit second_commit migration_commit installed_commit
  product_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
  source_dir="/tmp/omarchy-news-radar-local-latest"
  edition_dir="/tmp/omarchy-news-radar-local-edition"
  # The literal is expanded only by the disposable guest's shell.
  # shellcheck disable=SC2016
  plugin_dir='$HOME/.config/omarchy/plugins/io.github.mtolhuys.news-radar'

  log "Staging a clean local News Radar checkout"
  tar -C "$product_root" --exclude=.git --exclude=dist --exclude='__pycache__' -cf - . | ssh_guest \
    "mkdir -p '$source_dir' && tar -C '$source_dir' -xf -"
  ssh_guest "git -C '$source_dir' init -q && git -C '$source_dir' add . && \
    git -C '$source_dir' -c user.name=PluginLab -c user.email=lab@invalid commit -qm candidate"
  first_commit="$(ssh_guest "git -C '$source_dir' rev-parse HEAD")" || return 1
  ssh_guest "cp '$source_dir/manifest.json' /tmp/news-radar-current-manifest.json && \
    python3 '$source_dir/tests/lab/prepare_fixtures.py' '$source_dir/tests/fixtures/feed-valid.json' /tmp/news-radar-local-fixtures && \
    mkdir -p '$edition_dir/assets' && cp /tmp/news-radar-local-fixtures/valid.json '$edition_dir/events.json' && \
    cp -a /tmp/news-radar-local-fixtures/assets/images '$edition_dir/assets/images' && \
    digest=\$(sha256sum '$edition_dir/events.json' | cut -d' ' -f1) && \
    printf 'sourceRevision=%s\neventsSha256=%s\n' '$first_commit' \"\$digest\" >'$edition_dir/BUILD-INFO.txt'"

  log "Installing the exact clean checkout and a validated pictured edition through make local-latest"
  ssh_session "cd '$source_dir' && OMARCHY_NEWS_RADAR_TEST_MODE=1 OMARCHY_NEWS_RADAR_TEST_EDITION='$edition_dir' make local-latest" \
    >"$RUN_DIR/news-radar-local-latest-install.log" || return 1
  helper="$plugin_dir/bin/news-radar-client"
  wait_for_guest_state "local-latest installs the exact source, default-on bar, real-mode cache, and local image" 20 ssh_session \
    "test \"\$(git -C $plugin_dir rev-parse HEAD)\" = '$first_commit' && \
     test \"\$(realpath -e -- \"\$(git -C $plugin_dir remote get-url origin)\")\" = '$source_dir' && \
     omarchy-plugin-list --json | jq -e 'any(.[]; .id == \"io.github.mtolhuys.news-radar\" and .enabled == true)' && \
     (jq -e '.preferences.barVisible == true and .preferences.imagesVisible == true' \"\${XDG_STATE_HOME:-\$HOME/.local/state}/omarchy-news-radar/state.json\" 2>/dev/null || \
      test ! -e \"\${XDG_STATE_HOME:-\$HOME/.local/state}/omarchy-news-radar/state.json\") && \
     jq -e '.sourceRevision == \"$first_commit\"' \"\${XDG_CACHE_HOME:-\$HOME/.cache}/omarchy-news-radar/local-edition.json\" && \
     $helper project --section front-page --installed-json '[]' --query '' | jq -e 'any(.events[]; (.imageUrl // \"\") | startswith(\"file://\"))'" || return 1
  ssh_session "omarchy-shell shell debugBarGeometry" >"$RUN_DIR/news-radar-local-latest-bar.json" || return 1
  jq -e 'any(.[]; .id == "io.github.mtolhuys.news-radar" and .section == "right" and .visible == true and .width > 0)' \
    "$RUN_DIR/news-radar-local-latest-bar.json" >/dev/null || return 1
  capture_console "success-news-radar-local-latest-pictured-bar"

  log "Fast-forwarding the installed clone to the next committed source revision"
  ssh_guest "printf '\nLocal latest lifecycle fixture.\n' >>'$source_dir/CHANGELOG.md' && \
    git -C '$source_dir' add CHANGELOG.md && \
    git -C '$source_dir' -c user.name=PluginLab -c user.email=lab@invalid commit -qm next"
  second_commit="$(ssh_guest "git -C '$source_dir' rev-parse HEAD")" || return 1
  [[ $first_commit != "$second_commit" ]] || return 1
  ssh_guest "digest=\$(sha256sum '$edition_dir/events.json' | cut -d' ' -f1) && \
    printf 'sourceRevision=%s\neventsSha256=%s\n' '$second_commit' \"\$digest\" >'$edition_dir/BUILD-INFO.txt'"
  ssh_session "cd '$source_dir' && OMARCHY_NEWS_RADAR_TEST_MODE=1 OMARCHY_NEWS_RADAR_TEST_EDITION='$edition_dir' make local-latest" \
    >"$RUN_DIR/news-radar-local-latest-update.log" || return 1
  installed_commit="$(ssh_session "git -C $plugin_dir rev-parse HEAD")" || return 1
  [[ $installed_commit == "$second_commit" ]] || return 1
  ssh_session "cd '$source_dir' && OMARCHY_NEWS_RADAR_TEST_MODE=1 OMARCHY_NEWS_RADAR_TEST_EDITION='$edition_dir' make local-latest" \
    >"$RUN_DIR/news-radar-local-latest-idempotent.log" || return 1
  grep -Fq 'is up to date.' "$RUN_DIR/news-radar-local-latest-idempotent.log" || return 1

  log "Refusing dirty source without disturbing the installed revision"
  ssh_guest "printf '\nUncommitted fixture.\n' >>'$source_dir/CHANGELOG.md'"
  if ssh_session "cd '$source_dir' && OMARCHY_NEWS_RADAR_TEST_MODE=1 OMARCHY_NEWS_RADAR_TEST_EDITION='$edition_dir' make local-latest" \
    >"$RUN_DIR/news-radar-local-latest-dirty.log" 2>&1; then
    echo "local-latest accepted an uncommitted source tree" >&2
    return 1
  fi
  grep -Fq 'source checkout has uncommitted changes' "$RUN_DIR/news-radar-local-latest-dirty.log" || return 1
  [[ $(ssh_session "git -C $plugin_dir rev-parse HEAD") == "$second_commit" ]] || return 1
  ssh_guest "git -C '$source_dir' restore CHANGELOG.md"

  ssh_session "omarchy-plugin-remove io.github.mtolhuys.news-radar --yes" >/dev/null || return 1
  wait_for_guest_state "local-latest installation removes cleanly" 15 ssh_session \
    "test ! -e $plugin_dir && omarchy-plugin-list --json | jq -e 'all(.[]; .id != \"io.github.mtolhuys.news-radar\")'" || return 1
  log "Migrating the exact old panel-only placement to the default-on newspaper"
  ssh_guest "jq '.kinds = [\"panel\"] | .entryPoints = {panel: \"src/Panel.qml\"} | del(.barWidget)' \
    /tmp/news-radar-current-manifest.json >'$source_dir/manifest.json' && \
    git -C '$source_dir' add manifest.json && \
    git -C '$source_dir' -c user.name=PluginLab -c user.email=lab@invalid commit -qm panel-only-preview"
  ssh_session "omarchy-plugin-add '$source_dir' --enable --yes" >/dev/null || return 1
  helper="$plugin_dir/bin/news-radar-client"
  ssh_session "$helper set-preferences --bar-visible false --images-visible false" >/dev/null || return 1
  wait_for_guest_state "panel-only preview occupies its legacy plugin location" 15 ssh_session \
    "jq -e 'any(.plugins[]?; .id == \"io.github.mtolhuys.news-radar\") and ([.bar.layout.left[]?, .bar.layout.center[]?, .bar.layout.right[]?] | all(.id != \"io.github.mtolhuys.news-radar\"))' \"\$HOME/.config/omarchy/shell.json\"" || return 1
  ssh_guest "cp /tmp/news-radar-current-manifest.json '$source_dir/manifest.json' && \
    git -C '$source_dir' add manifest.json && \
    git -C '$source_dir' -c user.name=PluginLab -c user.email=lab@invalid commit -qm restore-pictured-newspaper"
  migration_commit="$(ssh_guest "git -C '$source_dir' rev-parse HEAD")" || return 1
  ssh_guest "digest=\$(sha256sum '$edition_dir/events.json' | cut -d' ' -f1) && \
    printf 'sourceRevision=%s\neventsSha256=%s\n' '$migration_commit' \"\$digest\" >'$edition_dir/BUILD-INFO.txt'"
  ssh_session "cd '$source_dir' && OMARCHY_NEWS_RADAR_TEST_MODE=1 OMARCHY_NEWS_RADAR_TEST_EDITION='$edition_dir' make local-latest" \
    >"$RUN_DIR/news-radar-local-latest-migration.log" || return 1
  grep -Fq 'Migrated the panel-only preview' "$RUN_DIR/news-radar-local-latest-migration.log" || return 1
  wait_for_guest_state "migration restores one right-side bar entry and the visual defaults" 20 ssh_session \
    "jq -e '([.plugins[]? | select(.id == \"io.github.mtolhuys.news-radar\")] | length == 0) and ([.bar.layout.right[]? | select(.id == \"io.github.mtolhuys.news-radar\")] | length == 1)' \"\$HOME/.config/omarchy/shell.json\" && \
     jq -e '.preferences.barVisible == true and .preferences.imagesVisible == true' \"\${XDG_STATE_HOME:-\$HOME/.local/state}/omarchy-news-radar/state.json\" && \
     omarchy-plugin-list --json | jq -e 'any(.[]; .id == \"io.github.mtolhuys.news-radar\" and .enabled == true)'" || return 1
  capture_console "success-news-radar-local-latest-migrated-bar"
  ssh_session "omarchy-plugin-remove io.github.mtolhuys.news-radar --yes" >/dev/null || return 1
  wait_for_guest_state "migrated local-latest installation removes cleanly" 15 ssh_session \
    "test ! -e $plugin_dir && omarchy-plugin-list --json | jq -e 'all(.[]; .id != \"io.github.mtolhuys.news-radar\")'" || return 1
  capture_console "success-news-radar-local-latest-removed"
  printf 'ok - make local-latest passed real pictured import, install, update, idempotence, refusal, legacy migration, defaults, and removal assertions\n'
}
