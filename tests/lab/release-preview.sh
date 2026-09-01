#!/bin/bash

# Networked release-only marketing capture. Deterministic acceptance remains
# fixture-driven; this journey renders the fixed public Pages edition inside a
# disposable guest and records one exact Matte Black window crop.

omarchy_host_test() {
  local product_root plugin_dir helper preview_address viewport_width viewport_height start_epoch
  qmp_pointer_move_preview() {
    local width="$1" height="$2" x="$3" y="$4" qx qy response
    qx=$((x * 32767 / (width - 1)))
    qy=$((y * 32767 / (height - 1)))
    response=$(qmp "\"input-send-event\", \"arguments\": {\"events\": [{\"type\":\"abs\",\"data\":{\"axis\":\"x\",\"value\":$qx}},{\"type\":\"abs\",\"data\":{\"axis\":\"y\",\"value\":$qy}}]}")
    ! grep -q '"error"' <<<"$response"
  }
  product_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
  start_epoch="$(date +%s)"

  log "Staging and installing the exact local News Radar candidate"
  tar -C "$product_root" --exclude=.git --exclude=dist --exclude='__pycache__' -cf - . | ssh_guest \
    "rm -rf /tmp/omarchy-news-radar-preview && mkdir -p /tmp/omarchy-news-radar-preview && tar -C /tmp/omarchy-news-radar-preview -xf -"
  ssh_guest "git -C /tmp/omarchy-news-radar-preview init -q && \
    git -C /tmp/omarchy-news-radar-preview add . && \
    git -C /tmp/omarchy-news-radar-preview -c user.name=PluginLab -c user.email=lab@invalid commit -qm candidate"
  ssh_session "omarchy-plugin-add /tmp/omarchy-news-radar-preview --enable --yes" \
    >"$RUN_DIR/news-radar-preview-install.log" || return 1

  # The literal is expanded only by the disposable guest's shell.
  # shellcheck disable=SC2016
  plugin_dir='$HOME/.config/omarchy/plugins/io.github.mtolhuys.news-radar'
  helper="$plugin_dir/bin/news-radar-client"
  wait_for_guest_state "preview candidate is enabled" 20 ssh_session \
    "omarchy-plugin-list --json | jq -e 'any(.[]; .id == \"io.github.mtolhuys.news-radar\" and .enabled == true)'" || return 1

  log "Refreshing the fixed public edition and applying Matte Black"
  ssh_session "$helper refresh" >"$RUN_DIR/news-radar-preview-refresh.json" || return 1
  wait_for_guest_state "public edition contains current stories and mirrored images" 30 ssh_session \
    "jq -e '.events | length > 0 and any(.[]; (.image.path // \"\") | startswith(\"assets/images/\"))' \
      \"\${XDG_CACHE_HOME:-\$HOME/.cache}/omarchy-news-radar/feed.json\"" || return 1
  ssh_session "omarchy-theme-set matte-black >/dev/null && omarchy-shell shell summon io.github.mtolhuys.news-radar" || return 1
  wait_for_guest_state "public edition is rendered by the local candidate" 30 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | \
      jq -e '.opened == true and .storyCount > 0 and .unreadCount > 0 and (.status == \"Current\" or .status == \"Cached\")'" || return 1

  preview_address="$(ssh_session "hyprctl -j clients | jq -er '.[] | select(.title == \"📰 Omarchy News Radar\") | .address'")" || return 1
  ssh_session "hyprctl dispatch 'hl.dsp.window.fullscreen({ window = \"address:$preview_address\", mode = \"maximized\", action = \"unset\" })' >/dev/null && \
    hyprctl dispatch 'hl.dsp.window.resize({ window = \"address:$preview_address\", x = 1240, y = 740 })' >/dev/null && \
    hyprctl dispatch 'hl.dsp.window.move({ window = \"address:$preview_address\", x = 20, y = 40 })' >/dev/null" || return 1
  wait_for_guest_state "release preview has a complete unobscured window boundary" 15 ssh_session \
    "hyprctl -j clients | jq -e 'any(.[]; .address == \"$preview_address\" and .title == \"📰 Omarchy News Radar\" and .at == [20, 40] and .size == [1240, 740])'" || return 1
  ssh_session "hyprctl -j clients | jq '.[] | select(.address == \"$preview_address\") | {at, size, title}'" \
    >"$RUN_DIR/news-radar-release-preview-geometry.json" || return 1
  viewport_width="$(ssh_session "hyprctl -j monitors | jq -r '.[0].width'")" || return 1
  viewport_height="$(ssh_session "hyprctl -j monitors | jq -r '.[0].height'")" || return 1
  qmp_pointer_move_preview "$viewport_width" "$viewport_height" 4 4 || return 1
  sleep 2
  capture_console "success-news-radar-release-preview-matte-black"

  press esc
  wait_for_guest_state "preview closes without an owned helper" 15 ssh_session \
    "hyprctl -j clients | jq -e 'all(.[]; .title != \"📰 Omarchy News Radar\")' && ! pgrep -u \"\$USER\" -f '[/]bin/news-radar-client'" || return 1
  ssh_session "omarchy-plugin-remove io.github.mtolhuys.news-radar --yes" >/dev/null || return 1
  wait_for_guest_state "preview candidate removes cleanly" 15 ssh_session \
    "test ! -e $plugin_dir && omarchy-plugin-list --json | jq -e 'all(.[]; .id != \"io.github.mtolhuys.news-radar\")'" || return 1
  ssh_session "journalctl --user --since '@$start_epoch' --no-pager" >"$RUN_DIR/news-radar-release-preview-journal.log" || true
  if grep -E 'io\.github\.mtolhuys\.news-radar.*(failed to load|ReferenceError|TypeError)|Panel\.qml.*(error|Error)' \
    "$RUN_DIR/news-radar-release-preview-journal.log"; then
    return 1
  fi
  printf 'ok - local candidate rendered the fixed public edition in the unobscured Matte Black release frame\n'
}
