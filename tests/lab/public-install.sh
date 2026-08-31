#!/bin/bash

# This scenario intentionally stays pending until the owner creates a public
# repository. It never substitutes a local path for the public clone proof.

omarchy_host_test() {
  local public_url expected_commit plugin_dir shortcut actual_commit start_epoch
  public_url="${OMARCHY_NEWS_RADAR_PUBLIC_URL:-}"
  expected_commit="${OMARCHY_NEWS_RADAR_EXPECTED_COMMIT:-}"
  if [[ -z $public_url || -z $expected_commit ]]; then
    printf 'pending - set the authorized public URL and expected 40-character release commit\n'
    return 77
  fi
  if [[ ! $public_url =~ ^https://github\.com/mtolhuys/omarchy-news-radar(\.git)?$ ]] || [[ ! $expected_commit =~ ^[0-9a-f]{40}$ ]]; then
    printf 'refusing unexpected public repository identity or commit\n' >&2
    return 1
  fi

  start_epoch="$(date +%s)"
  log "Installing the authorized public release candidate"
  ssh_session "omarchy-plugin-add '$public_url' --enable --yes" >"$RUN_DIR/news-radar-public-install.log" || return 1
  # The literal is expanded by the disposable guest's shell.
  # shellcheck disable=SC2016
  plugin_dir='$HOME/.config/omarchy/plugins/io.github.mtolhuys.news-radar'
  shortcut="$plugin_dir/bin/news-radar-shortcut"
  actual_commit="$(ssh_session "git -C $plugin_dir rev-parse HEAD")"
  [[ $actual_commit == "$expected_commit" ]] || {
    printf 'public clone resolved %s, expected %s\n' "$actual_commit" "$expected_commit" >&2
    return 1
  }
  wait_for_guest_state "public clone is enabled as the panel-only release commit" 20 ssh_session \
    "omarchy-plugin-list --json | jq -e 'any(.[]; .id == \"io.github.mtolhuys.news-radar\" and .enabled == true)' && \
     jq -e '.version == \"0.1.0\" and .kinds == [\"panel\"] and (.entryPoints | keys == [\"panel\"])' $plugin_dir/manifest.json" || return 1

  log "Proving documented public shortcut setup and rendered launch"
  ssh_session "$shortcut status" >"$RUN_DIR/news-radar-public-shortcut-status.json" || return 1
  jq -e '.status == "ok" and .classification == "free" and .binding == "SUPER + ALT + N"' \
    "$RUN_DIR/news-radar-public-shortcut-status.json" >/dev/null || return 1
  ssh_session "$shortcut install" >"$RUN_DIR/news-radar-public-shortcut-installed.json" || return 1
  press meta_l-alt-n
  wait_for_guest_state "public shortcut opens the installed panel" 20 ssh_session \
    "hyprctl -j layers | jq -e '[.. | objects | select(.namespace? == \"omarchy-news-radar\")] | length >= 1'" || return 1
  capture_console "success-news-radar-public-install"
  press esc
  wait_for_guest_state "public panel closes without an owned helper" 15 ssh_session \
    "hyprctl -j layers | jq -e '[.. | objects | select(.namespace? == \"omarchy-news-radar\")] | length == 0' && ! pgrep -u \"\$USER\" -f '[/]bin/news-radar-client'" || return 1

  log "Removing the shortcut before the public plugin"
  ssh_session "$shortcut remove" >"$RUN_DIR/news-radar-public-shortcut-removed.json" || return 1
  ssh_session "hyprctl binds -j | jq -e '[.[] | select(((.key // \"\") | ascii_upcase) == \"N\" and .modmask == 72)] | length == 0' && \
    hyprctl binds -j | jq -e '[.[] | select((.description // \"\") == \"Editor\" and ((.key // \"\") | ascii_upcase) == \"N\" and .modmask == 65)] | length == 1'" || return 1
  ssh_session "omarchy-plugin-remove io.github.mtolhuys.news-radar --yes" || return 1
  wait_for_guest_state "public plugin removal unloads the exact clone" 15 ssh_session \
    "test ! -e $plugin_dir && omarchy-plugin-list --json | jq -e 'all(.[]; .id != \"io.github.mtolhuys.news-radar\")'" || return 1
  ssh_session "journalctl --user --since '@$start_epoch' --no-pager" >"$RUN_DIR/news-radar-public-journal.log" || true
  if grep -E 'io\.github\.mtolhuys\.news-radar.*(failed to load|ReferenceError|TypeError)|Panel\.qml.*(error|Error)' \
    "$RUN_DIR/news-radar-public-journal.log"; then
    return 1
  fi
  printf 'ok - public URL resolved the exact release commit and passed install, shortcut, render, and removal\n'
}
