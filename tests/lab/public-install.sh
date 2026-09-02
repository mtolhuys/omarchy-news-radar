#!/bin/bash

# This scenario proves the authorized public repository and fixed Pages feed.
# It never substitutes a local path for the public clone proof.

omarchy_host_test() {
  local public_url expected_commit plugin_dir shortcut launcher actual_commit selected_id start_epoch
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
  launcher="$plugin_dir/bin/news-radar-launcher"
  actual_commit="$(ssh_session "git -C $plugin_dir rev-parse HEAD")"
  [[ $actual_commit == "$expected_commit" ]] || {
    printf 'public clone resolved %s, expected %s\n' "$actual_commit" "$expected_commit" >&2
    return 1
  }
  wait_for_guest_state "public clone is enabled with paired panel and newspaper entry points" 20 ssh_session \
    "omarchy-plugin-list --json | jq -e 'any(.[]; .id == \"io.github.mtolhuys.news-radar\" and .enabled == true)' && \
     jq -e '.version == \"0.2.2\" and .kinds == [\"panel\",\"bar-widget\"] and (.entryPoints | keys == [\"barWidget\",\"panel\"])' $plugin_dir/manifest.json" || return 1

  log "Proving documented public Apps-menu and shortcut setup"
  ssh_session "$launcher install" >"$RUN_DIR/news-radar-public-launcher-installed.json" || return 1
  wait_for_guest_state "public launcher entry is installed with its icon" 15 ssh_session \
    "$launcher status | jq -e '.state == \"installed\"' && \
     test -f \"\${XDG_DATA_HOME:-\$HOME/.local/share}/applications/io.github.mtolhuys.news-radar.desktop\" && \
     test -f \"\${XDG_DATA_HOME:-\$HOME/.local/share}/icons/hicolor/scalable/apps/io.github.mtolhuys.news-radar.svg\"" || return 1
  press meta_l-spc
  wait_for_guest_state "public Apps menu opens" 10 ssh_session \
    "hyprctl -j layers | jq -e '[.. | objects | select(.namespace? == \"omarchy-menu\")] | length >= 1'" || return 1
  type_text "omarchy news radar"
  sleep 1
  press ret
  wait_for_guest_state "public Apps entry opens the installed panel" 20 ssh_session \
    "hyprctl -j clients | jq -e 'any(.[]; .title == \"📰 Omarchy News Radar\")'" || return 1
  wait_for_guest_state "public panel loads the fixed published edition with explicit unread state" 30 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.storyCount > 0 and .selectedIsUnread == true and .unreadCount > 0 and (.status == \"Updated\" or .status == \"No newer edition\" or .status == \"Cached\")'" || return 1
  capture_console "success-news-radar-public-app-launcher"
  selected_id="$(ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -r '.selectedId'")" || return 1
  [[ $selected_id =~ ^evt_[0-9a-f]{24}$ ]] || return 1
  press u
  wait_for_guest_state "public reader persists only the selected story as read" 15 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.selectedIsUnread == false' && \
     jq -e --arg id '$selected_id' '.schemaVersion == 9 and .readOverrides[\$id] == true' \"\${XDG_STATE_HOME:-\$HOME/.local/state}/omarchy-news-radar/state.json\"" || return 1
  capture_console "success-news-radar-public-read-state"
  press esc
  wait_for_guest_state "Apps-launched public panel closes" 15 ssh_session \
    "hyprctl -j clients | jq -e 'all(.[]; .title != \"📰 Omarchy News Radar\")' && ! pgrep -u \"\$USER\" -f '[/]bin/news-radar-client'" || return 1

  ssh_session "$shortcut status" >"$RUN_DIR/news-radar-public-shortcut-status.json" || return 1
  jq -e '.status == "ok" and .classification == "free" and .binding == "SUPER + ALT + N"' \
    "$RUN_DIR/news-radar-public-shortcut-status.json" >/dev/null || return 1
  ssh_session "$shortcut install" >"$RUN_DIR/news-radar-public-shortcut-installed.json" || return 1
  press meta_l-alt-n
  wait_for_guest_state "public shortcut opens the installed panel" 20 ssh_session \
    "hyprctl -j clients | jq -e 'any(.[]; .title == \"📰 Omarchy News Radar\")'" || return 1
  capture_console "success-news-radar-public-install"
  press esc
  wait_for_guest_state "public panel closes without an owned helper" 15 ssh_session \
    "hyprctl -j clients | jq -e 'all(.[]; .title != \"📰 Omarchy News Radar\")' && ! pgrep -u \"\$USER\" -f '[/]bin/news-radar-client'" || return 1

  log "Removing the shortcut before the public plugin"
  ssh_session "$shortcut remove" >"$RUN_DIR/news-radar-public-shortcut-removed.json" || return 1
  ssh_session "hyprctl binds -j | jq -e '[.[] | select(((.key // \"\") | ascii_upcase) == \"N\" and .modmask == 72)] | length == 0' && \
    hyprctl binds -j | jq -e '[.[] | select((.description // \"\") == \"Editor\" and ((.key // \"\") | ascii_upcase) == \"N\" and .modmask == 65)] | length == 1'" || return 1
  ssh_session "$launcher remove" >"$RUN_DIR/news-radar-public-launcher-removed.json" || return 1
  ssh_session "omarchy-plugin-remove io.github.mtolhuys.news-radar --yes" || return 1
  wait_for_guest_state "public plugin removal unloads the exact clone" 15 ssh_session \
    "test ! -e $plugin_dir && omarchy-plugin-list --json | jq -e 'all(.[]; .id != \"io.github.mtolhuys.news-radar\")'" || return 1
  ssh_session "journalctl --user --since '@$start_epoch' --no-pager" >"$RUN_DIR/news-radar-public-journal.log" || true
  if grep -E 'io\.github\.mtolhuys\.news-radar.*(failed to load|ReferenceError|TypeError)|Panel\.qml.*(error|Error)' \
    "$RUN_DIR/news-radar-public-journal.log"; then
    return 1
  fi
  printf 'ok - public URL resolved the exact release commit and passed launcher, shortcut, render, and removal\n'
}
