#!/bin/bash

# Full product-owned journey. The harness runs this function only inside a
# disposable Omarchy guest; the daily host is used solely to stage source and
# retain evidence.

omarchy_host_test() {
  local product_root lab_root alttab_root omadock_root start_epoch before_hash after_hash before_change_count
  local helper shortcut launcher plugin_dir viewport_width viewport_height monitor_name bar_x bar_y tune_x tune_y
  local control_x control_y window_before_width window_after_width window_x window_y window_width window_height window_initial_maximized
  local settings_center_x settings_center_y
  local open_started_ms open_ready_ms dense_started_ms dense_ready_ms close_started_ms close_ready_ms
  local shell_rss_open shell_rss_closed projection_seconds
  product_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
  lab_root="$(cd -- "$product_root/../../omarchy/plugin-lab" && pwd)"
  alttab_root="$(cd -- "$product_root/../hyprland-alttab" && pwd)"
  omadock_root="$(cd -- "$product_root/../omadock" && pwd)"
  # shellcheck source=/dev/null
  source "$lab_root/host-tests/helpers/pointer.sh"

  qmp_pointer_drag() {
    local width="$1" height="$2" from_x="$3" from_y="$4" to_x="$5" to_y="$6"
    local from_qx from_qy step step_x step_y step_qx step_qy response
    from_qx=$((from_x * 32767 / (width - 1)))
    from_qy=$((from_y * 32767 / (height - 1)))
    response=$(qmp "\"input-send-event\", \"arguments\": {\"events\": [{\"type\":\"abs\",\"data\":{\"axis\":\"x\",\"value\":$from_qx}},{\"type\":\"abs\",\"data\":{\"axis\":\"y\",\"value\":$from_qy}}]}")
    grep -q '"error"' <<<"$response" && return 1
    sleep 0.1
    response=$(qmp '"input-send-event", "arguments": {"events": [{"type":"btn","data":{"down":true,"button":"left"}}]}')
    grep -q '"error"' <<<"$response" && return 1
    sleep 0.2
    for step in 1 2 3 4; do
      step_x=$((from_x + (to_x - from_x) * step / 4))
      step_y=$((from_y + (to_y - from_y) * step / 4))
      step_qx=$((step_x * 32767 / (width - 1)))
      step_qy=$((step_y * 32767 / (height - 1)))
      response=$(qmp "\"input-send-event\", \"arguments\": {\"events\": [{\"type\":\"abs\",\"data\":{\"axis\":\"x\",\"value\":$step_qx}},{\"type\":\"abs\",\"data\":{\"axis\":\"y\",\"value\":$step_qy}}]}")
      grep -q '"error"' <<<"$response" && return 1
      sleep 0.12
    done
    response=$(qmp '"input-send-event", "arguments": {"events": [{"type":"btn","data":{"down":false,"button":"left"}}]}')
    grep -q '"error"' <<<"$response" && return 1
    sleep 0.5
  }

  qmp_pointer_scroll_down() {
    local width="$1" height="$2" x="$3" y="$4" count="${5:-6}"
    local qx qy response step
    qx=$((x * 32767 / (width - 1)))
    qy=$((y * 32767 / (height - 1)))
    response=$(qmp "\"input-send-event\", \"arguments\": {\"events\": [{\"type\":\"abs\",\"data\":{\"axis\":\"x\",\"value\":$qx}},{\"type\":\"abs\",\"data\":{\"axis\":\"y\",\"value\":$qy}}]}")
    grep -q '"error"' <<<"$response" && return 1
    for ((step = 0; step < count; step++)); do
      response=$(qmp '"input-send-event", "arguments": {"events": [{"type":"btn","data":{"down":true,"button":"wheel-down"}},{"type":"btn","data":{"down":false,"button":"wheel-down"}}]}')
      grep -q '"error"' <<<"$response" && return 1
      sleep 0.08
    done
    sleep 0.5
  }

  qmp_pointer_move() {
    local width="$1" height="$2" x="$3" y="$4"
    local qx qy response
    qx=$((x * 32767 / (width - 1)))
    qy=$((y * 32767 / (height - 1)))
    response=$(qmp "\"input-send-event\", \"arguments\": {\"events\": [{\"type\":\"abs\",\"data\":{\"axis\":\"x\",\"value\":$qx}},{\"type\":\"abs\",\"data\":{\"axis\":\"y\",\"value\":$qy}}]}")
    grep -q '"error"' <<<"$response" && return 1
    sleep 0.2
  }

  radar_control_geometry() {
    local method="$1" geometry geometry_raw window_position local_x local_y
    geometry_raw="$(ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar '$method' ''")" || return 1
    printf '%s\n' "$geometry_raw" >"$RUN_DIR/news-radar-${method}.raw"
    geometry="$(awk '/^\{.*\}$/ { value = $0 } END { print value }' <<<"$geometry_raw")"
    [[ -n $geometry ]] || return 1
    [[ $(jq -r '.visible' <<<"$geometry") == true ]] || return 1
    window_position="$(ssh_session "hyprctl -j clients | jq -r '.[] | select(.title == \"📰 Omarchy News Radar\") | [.at[0], .at[1]] | @tsv'")" || return 1
    read -r window_x window_y <<<"$window_position"
    local_x="$(jq -r '(.x + (.width / 2) | floor)' <<<"$geometry")" || return 1
    local_y="$(jq -r '(.y + (.height / 2) | floor)' <<<"$geometry")" || return 1
    control_x=$((window_x + local_x))
    control_y=$((window_y + local_y))
  }
  start_epoch="$(date +%s)"

  log "Staging the exact News Radar candidate in the disposable guest"
  tar -C "$product_root" --exclude=.git --exclude=dist --exclude='__pycache__' -cf - . | ssh_guest \
    "rm -rf /tmp/omarchy-news-radar-candidate && mkdir -p /tmp/omarchy-news-radar-candidate && tar -C /tmp/omarchy-news-radar-candidate -xf -"
  ssh_guest "git -C /tmp/omarchy-news-radar-candidate init -q && \
    git -C /tmp/omarchy-news-radar-candidate add . && \
    git -C /tmp/omarchy-news-radar-candidate -c user.name=PluginLab -c user.email=lab@invalid commit -qm candidate"
  tar -C "$alttab_root" --exclude=.git -cf - . | ssh_guest \
    "rm -rf /tmp/hyprland-alttab-candidate && mkdir -p /tmp/hyprland-alttab-candidate && tar -C /tmp/hyprland-alttab-candidate -xf -"
  tar -C "$omadock_root" --exclude=.git -cf - . | ssh_guest \
    "rm -rf /tmp/omadock-candidate && mkdir -p /tmp/omadock-candidate && tar -C /tmp/omadock-candidate -xf -"
  ssh_guest "git -C /tmp/hyprland-alttab-candidate init -q && git -C /tmp/hyprland-alttab-candidate add . && \
    git -C /tmp/hyprland-alttab-candidate -c user.name=PluginLab -c user.email=lab@invalid commit -qm candidate && \
    git -C /tmp/omadock-candidate init -q && git -C /tmp/omadock-candidate add . && \
    git -C /tmp/omadock-candidate -c user.name=PluginLab -c user.email=lab@invalid commit -qm candidate"
  ssh_guest "cd /tmp/omarchy-news-radar-candidate && make test && make validate" \
    >"$RUN_DIR/news-radar-source-tests.log" || return 1
  ssh_guest "make -C /tmp/hyprland-alttab-candidate test && \
    make -C /tmp/omadock-candidate test" \
    >"$RUN_DIR/news-radar-companion-source-tests.log" || return 1
  ssh_guest "python3 /tmp/omarchy-news-radar-candidate/tests/lab/prepare_fixtures.py \
    /tmp/omarchy-news-radar-candidate/tests/fixtures/feed-valid.json /tmp/news-radar-fixtures" || return 1

  log "Installing Radar, its exact companion candidates, and a synthetic relevance plugin"
  ssh_session "omarchy-plugin-add /tmp/hyprland-alttab-candidate --enable --yes && \
    omarchy-plugin-add /tmp/omadock-candidate --enable --yes" \
    >"$RUN_DIR/news-radar-companion-install.log" || return 1
  ssh_session "omarchy-plugin-add /tmp/omarchy-news-radar-candidate --enable --yes" \
    >"$RUN_DIR/news-radar-install.log" || return 1
  ssh_guest "rm -rf /tmp/news-radar-installed-plugin && mkdir -p /tmp/news-radar-installed-plugin && \
    printf '%s\n' '{\"schemaVersion\":1,\"id\":\"io.github.mtolhuys.disk-lens\",\"name\":\"Disk Lens fixture\",\"version\":\"1.0.0\",\"kinds\":[\"service\"],\"entryPoints\":{\"service\":\"Service.qml\"}}' >/tmp/news-radar-installed-plugin/manifest.json && \
    printf '%s\n' 'import QtQuick' 'Item {}' >/tmp/news-radar-installed-plugin/Service.qml && \
    git -C /tmp/news-radar-installed-plugin init -q && git -C /tmp/news-radar-installed-plugin add . && \
    git -C /tmp/news-radar-installed-plugin -c user.name=PluginLab -c user.email=lab@invalid commit -qm fixture"
  ssh_session "omarchy-plugin-add /tmp/news-radar-installed-plugin --enable --yes" >/dev/null || return 1

  wait_for_guest_state "candidate, companions, and relevance fixture are installed and enabled" 20 ssh_session \
    "omarchy-plugin-list --json | jq -e 'any(.[]; .id == \"io.github.mtolhuys.news-radar\" and .enabled == true) and any(.[]; .id == \"io.github.mtolhuys.disk-lens\" and .enabled == true) and any(.[]; .id == \"vbrosseau.alttab\" and .enabled == true) and any(.[]; .id == \"omadock\" and .enabled == true)'" || return 1
  ssh_session "omarchy-shell shell listPlugins" >"$RUN_DIR/news-radar-plugin-list.json" || return 1
  jq -e 'any(.[]; .id == "io.github.mtolhuys.news-radar" and .kinds == ["panel", "bar-widget"] and .enabled == true)' \
    "$RUN_DIR/news-radar-plugin-list.json" >/dev/null || return 1

  # The literal is expanded by the disposable guest's shell, not the host.
  # shellcheck disable=SC2016
  plugin_dir='$HOME/.config/omarchy/plugins/io.github.mtolhuys.news-radar'
  helper="$plugin_dir/bin/news-radar-client"
  shortcut="$plugin_dir/bin/news-radar-shortcut"
  launcher="$plugin_dir/bin/news-radar-launcher"

  log "Installing the inert source-opening shim and isolated loopback fixture boundary"
  ssh_guest "cp /tmp/news-radar-fixtures/valid.json /tmp/news-radar-fixtures/current.json && \
    systemd-run --user --unit=omarchy-news-radar-fixture --collect --quiet -- \
      python3 -m http.server 18765 --bind 127.0.0.1 --directory /tmp/news-radar-fixtures"
  wait_for_guest_state "loopback fixture server is ready" 10 ssh_guest \
    "curl -fsS http://127.0.0.1:18765/current.json >/dev/null" || return 1
  ssh_session "mkdir -p \"\$HOME/.local/bin\" \"\$HOME/.local/state/omarchy-news-radar\" && \
    cp $plugin_dir/tests/lab/fixtures/xdg-open \"\$HOME/.local/bin/xdg-open\" && chmod +x \"\$HOME/.local/bin/xdg-open\" && \
    printf '%s\n' \
      'hl.env(\"OMARCHY_NEWS_RADAR_TEST_MODE\", \"1\")' \
      'hl.env(\"OMARCHY_NEWS_RADAR_TEST_FEED_URL\", \"http://127.0.0.1:18765/current.json\")' \
      'hl.env(\"PATH\", os.getenv(\"HOME\") .. \"/.local/bin:\" .. (os.getenv(\"PATH\") or \"/usr/bin\"))' \
      'dofile(os.getenv(\"HOME\") .. \"/.config/omarchy/plugins/vbrosseau.alttab/omarchy-plugin/alttab-bindings.lua\")' \
      >>\"\$HOME/.config/hypr/bindings.lua\" && \
    hyprctl reload >/dev/null && test -z \"\$(hyprctl configerrors)\" && omarchy-restart-shell"
  wait_for_guest_state "restarted shell uses the exact candidate" 30 ssh_session \
    "omarchy-shell shell ping >/dev/null && omarchy-plugin-list --json | jq -e 'any(.[]; .id == \"io.github.mtolhuys.news-radar\" and .enabled == true)'" || return 1

  log "Installing and launching the receipt-backed Apps-menu entry"
  ssh_session "$launcher install" >"$RUN_DIR/news-radar-launcher-installed.json" || return 1
  wait_for_guest_state "launcher entry and newspaper icon are managed exact files" 15 ssh_session \
    "$launcher status | jq -e '.state == \"installed\" and .installed == true' && \
     grep -Fx 'Exec=omarchy-shell shell summon io.github.mtolhuys.news-radar' \"\${XDG_DATA_HOME:-\$HOME/.local/share}/applications/io.github.mtolhuys.news-radar.desktop\" && \
     test -f \"\${XDG_DATA_HOME:-\$HOME/.local/share}/icons/hicolor/scalable/apps/io.github.mtolhuys.news-radar.svg\"" || return 1
  press meta_l-spc
  wait_for_guest_state "Omarchy menu opens for the application search journey" 10 ssh_session \
    "hyprctl -j layers | jq -e '[.. | objects | select(.namespace? == \"omarchy-menu\")] | length >= 1'" || return 1
  type_text "omarchy news radar"
  sleep 1
  capture_console "success-news-radar-00-app-launcher"
  press ret
  wait_for_guest_state "visible Apps-menu selection summons Radar" 15 ssh_session \
    "hyprctl -j clients | jq -e 'any(.[]; .title == \"📰 Omarchy News Radar\")'" || {
      ssh_session "hyprctl -j clients" >"$RUN_DIR/news-radar-app-launcher-failure-clients.json" 2>&1 || true
      ssh_session "journalctl --user --since '@$start_epoch' --no-pager" \
        >"$RUN_DIR/news-radar-app-launcher-failure-journal.log" 2>&1 || true
      ssh_session "systemctl --user --no-pager --all --type=service --type=scope" \
        >"$RUN_DIR/news-radar-app-launcher-failure-units.log" 2>&1 || true
      capture_console "failure-news-radar-app-launcher"
      return 1
    }
  press esc
  wait_for_guest_state "Apps-launched Radar closes through the normal lifecycle" 15 ssh_session \
    "hyprctl -j clients | jq -e 'all(.[]; .title != \"📰 Omarchy News Radar\")'" || return 1

  log "Proving the default newspaper placement and native geometry"
  wait_for_guest_state "newspaper occupies one visible right-section slot" 20 ssh_session \
    "omarchy-shell shell debugBarGeometry | jq -e 'any(.[]; .id == \"io.github.mtolhuys.news-radar\" and .section == \"right\" and .visible == true and .width > 0 and .height > 0)'" || {
      ssh_session "omarchy-shell shell debugBarGeometry" >"$RUN_DIR/news-radar-bar-failure.json" 2>&1 || true
      ssh_session "journalctl --user --since '@$start_epoch' --no-pager" >"$RUN_DIR/news-radar-bar-failure-journal.log" 2>&1 || true
      capture_console "failure-news-radar-bar"
      return 1
    }
  ssh_session "omarchy-shell shell debugBarGeometry" >"$RUN_DIR/news-radar-bar-visible.json" || return 1
  capture_console "success-news-radar-00-bar-visible"
  viewport_width="$(ssh_session "hyprctl -j monitors | jq -r '.[0].width'")"
  viewport_height="$(ssh_session "hyprctl -j monitors | jq -r '.[0].height'")"
  bar_x="$(jq -r '.[] | select(.id == "io.github.mtolhuys.news-radar") | (.x + (.width / 2) | floor)' "$RUN_DIR/news-radar-bar-visible.json")"
  bar_y="$(jq -r '.[] | select(.id == "io.github.mtolhuys.news-radar") | (.y + (.height / 2) | floor)' "$RUN_DIR/news-radar-bar-visible.json")"
  [[ $bar_x =~ ^[0-9]+$ && $bar_y =~ ^[0-9]+$ ]] || return 1
  wait_for_guest_state "startup refresh cached the valid edition" 15 ssh_session \
    "jq -e '.generatedAt == \"2026-08-31T14:00:00Z\"' \"\${XDG_CACHE_HOME:-\$HOME/.cache}/omarchy-news-radar/feed.json\"" || return 1
  ssh_guest "cp /tmp/news-radar-fixtures/later.json /tmp/news-radar-fixtures/current.json"
  qmp_pointer_tap "$viewport_width" "$viewport_height" "$bar_x" "$bar_y" middle
  wait_for_guest_state "middle click performs one bounded refresh" 15 ssh_session \
    "jq -e '.generatedAt == \"2026-08-31T14:02:00Z\"' \"\${XDG_CACHE_HOME:-\$HOME/.cache}/omarchy-news-radar/feed.json\"" || return 1
  ssh_guest "cp /tmp/news-radar-fixtures/valid.json /tmp/news-radar-fixtures/current.json"
  ssh_session "OMARCHY_NEWS_RADAR_TEST_MODE=1 OMARCHY_NEWS_RADAR_TEST_FEED_URL=http://127.0.0.1:18765/current.json $helper refresh" >/dev/null || return 1
  qmp_pointer_tap "$viewport_width" "$viewport_height" "$bar_x" "$bar_y" left
  wait_for_guest_state "left click on the newspaper opens the panel" 15 ssh_session \
    "hyprctl -j clients | jq -e 'any(.[]; .title == \"📰 Omarchy News Radar\")'" || {
      ssh_session "journalctl --user --since '@$start_epoch' --no-pager" >"$RUN_DIR/news-radar-panel-load-failure-journal.log" 2>&1 || true
      ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState ''" >"$RUN_DIR/news-radar-panel-load-failure-debug.log" 2>&1 || true
      capture_console "failure-news-radar-panel-load"
      return 1
    }
  wait_for_guest_state "AltTab resolves the exact enabled Radar window identity" 15 ssh_session \
    "qs -p \"\$OMARCHY_PATH/shell\" ipc call omarchy-alttab resolvedWindowIdentity '{\"appId\":\"org.quickshell\",\"title\":\"📰 Omarchy News Radar\"}' | jq -e '.pluginId == \"io.github.mtolhuys.news-radar\" and .name == \"Omarchy News Radar\" and .label == \"Omarchy News Radar\" and (.icon | endswith(\"/assets/io.github.mtolhuys.news-radar.svg\"))'" || return 1
  wait_for_guest_state "Omadock renders the same exact manifest identity in its live model" 15 ssh_session \
    "qs -p \"\$OMARCHY_PATH/shell\" ipc call omadock resolvedWindowIdentity '{\"appId\":\"org.quickshell\",\"title\":\"📰 Omarchy News Radar\"}' | jq -e '.pluginId == \"io.github.mtolhuys.news-radar\" and .name == \"Omarchy News Radar\" and .modelMatched == true and (.icon | endswith(\"/assets/io.github.mtolhuys.news-radar.svg\"))'" || return 1
  ssh_session "qs -p \"\$OMARCHY_PATH/shell\" ipc call omarchy-alttab resolvedWindowIdentity '{\"appId\":\"org.quickshell\",\"title\":\"Unrelated Quickshell window\"}' | jq -e 'length == 0' && \
    qs -p \"\$OMARCHY_PATH/shell\" ipc call omadock resolvedWindowIdentity '{\"appId\":\"org.quickshell\",\"title\":\"Unrelated Quickshell window\"}' | jq -e 'length == 0'" || return 1
  qmp_pointer_move "$viewport_width" "$viewport_height" "$((viewport_width / 2))" "$((viewport_height - 1))" || return 1
  sleep 1
  capture_console "success-news-radar-00-companion-dock-icon"
  qmp_pointer_move "$viewport_width" "$viewport_height" 4 4 || return 1
  press esc
  qmp_pointer_tap "$viewport_width" "$viewport_height" "$bar_x" "$bar_y" right
  wait_for_guest_state "right click persists hidden state with exact zero slot geometry" 15 ssh_session \
    "jq -e '.preferences.barVisible == false' \"\${XDG_STATE_HOME:-\$HOME/.local/state}/omarchy-news-radar/state.json\" && \
     omarchy-shell shell debugBarGeometry | jq -e 'any(.[]; .id == \"io.github.mtolhuys.news-radar\" and .visible == false and .width == 0 and .itemVisible == false)'" || return 1
  ssh_session "omarchy-shell shell debugBarGeometry" >"$RUN_DIR/news-radar-bar-hidden.json" || return 1
  capture_console "success-news-radar-00-bar-hidden-zero-gap"

  log "Proving free-chord inspection, installation, and live identity"
  before_hash="$(ssh_session "sha256sum \"\$HOME/.config/hypr/bindings.lua\" | cut -d' ' -f1")"
  ssh_session "$shortcut status" >"$RUN_DIR/news-radar-shortcut-status.json" || return 1
  after_hash="$(ssh_session "sha256sum \"\$HOME/.config/hypr/bindings.lua\" | cut -d' ' -f1")"
  [[ $before_hash == "$after_hash" ]] || return 1
  jq -e '.status == "ok" and .classification == "free" and .binding == "SUPER + ALT + N"' \
    "$RUN_DIR/news-radar-shortcut-status.json" >/dev/null || return 1
  ssh_session "$shortcut install" >"$RUN_DIR/news-radar-shortcut-installed.json" || return 1
  ssh_session "grep -F -- '-- BEGIN OMARCHY NEWS RADAR MANAGED SHORTCUT' \"\$HOME/.config/hypr/bindings.lua\" && \
    grep -F -- 'o.bind(\"SUPER + ALT + N\", \"Omarchy News Radar\"' \"\$HOME/.config/hypr/bindings.lua\" && \
    test -z \"\$(hyprctl configerrors)\" && \
    hyprctl binds -j | jq -e '[.[] | select((.description // \"\") == \"Omarchy News Radar\" and ((.key // \"\") | ascii_upcase) == \"N\" and .modmask == 72)] | length == 1' && \
    hyprctl binds -j | jq -e '[.[] | select((.description // \"\") == \"Editor\" and ((.key // \"\") | ascii_upcase) == \"N\" and .modmask == 65)] | length == 1'" || return 1

  log "Restoring the hidden newspaper from the rendered panel preference"
  press meta_l-alt-n
  wait_for_guest_state "shortcut opens the panel while its bar widget is hidden" 15 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.opened == true'" || return 1
  ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar showPreferences ''" >/dev/null || return 1
  wait_for_guest_state "Tune Your Radar is visibly open" 10 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.preferencesOpen == true'" || return 1
  capture_console "success-news-radar-00-tune-hidden"
  radar_control_geometry tuneNewspaperGeometry || return 1
  tune_x="$control_x"
  tune_y="$control_y"
  [[ $tune_x =~ ^[0-9]+$ && $tune_y =~ ^[0-9]+$ ]] || return 1
  qmp_pointer_tap "$viewport_width" "$viewport_height" "$tune_x" "$tune_y" left
  wait_for_guest_state "panel switch restores the newspaper" 15 ssh_session \
    "jq -e '.preferences.barVisible == true' \"\${XDG_STATE_HOME:-\$HOME/.local/state}/omarchy-news-radar/state.json\" && \
     omarchy-shell shell debugBarGeometry | jq -e 'any(.[]; .id == \"io.github.mtolhuys.news-radar\" and .visible == true and .width > 0)'" || return 1
  capture_console "success-news-radar-00-bar-restored-from-panel"
  press esc
  press esc

  log "Proving first use and the real QMP global shortcut route"
  ssh_guest "rm -f /tmp/news-radar-fixtures/current.json"
  ssh_session "rm -rf \"\${XDG_CACHE_HOME:-\$HOME/.cache}/omarchy-news-radar\" \"\${XDG_STATE_HOME:-\$HOME/.local/state}/omarchy-news-radar/state.json\""
  open_started_ms="$(date +%s%3N)"
  press meta_l-alt-n
  wait_for_guest_state "QMP Super+Alt+N opens the rendered Radar layer" 20 ssh_session \
    "hyprctl -j clients | jq -e 'any(.[]; .title == \"📰 Omarchy News Radar\")'" || return 1
  wait_for_guest_state "first-use failure has visible deterministic recovery" 20 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.opened == true and .status == \"No cache and failed\" and .storyCount == 0'" || {
      ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState ''" >"$RUN_DIR/news-radar-debug-first-use.json" 2>&1 || true
      ssh_session "journalctl --user --since '@$start_epoch' --no-pager" >"$RUN_DIR/news-radar-first-use-journal.log" 2>&1 || true
      capture_console "failure-news-radar-first-use"
      return 1
    }
  open_ready_ms="$(date +%s%3N)"
  capture_console "success-news-radar-01-first-use"
  press esc
  wait_for_guest_state "Escape closes first use and leaves no helper" 15 ssh_session \
    "hyprctl -j clients | jq -e 'all(.[]; .title != \"📰 Omarchy News Radar\")' && ! pgrep -u \"\$USER\" -f '[/]bin/news-radar-client'" || return 1

  log "Proving cached-first reading, offline preservation, and pointer close"
  ssh_guest "cp /tmp/news-radar-fixtures/valid.json /tmp/news-radar-fixtures/current.json"
  ssh_session "OMARCHY_NEWS_RADAR_TEST_MODE=1 OMARCHY_NEWS_RADAR_TEST_FEED_URL=http://127.0.0.1:18765/current.json $helper refresh" \
    >"$RUN_DIR/news-radar-seed-cache.json" || return 1
  ssh_guest "rm -f /tmp/news-radar-fixtures/current.json"
  press meta_l-alt-n
  wait_for_guest_state "cached fixture remains visible after offline refresh" 20 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.opened == true and .status == \"Offline\" and .storyCount > 0 and (.selectedTitle | length > 0)'" || return 1
  capture_console "success-news-radar-02-cached-offline"
  radar_control_geometry closeGeometry || return 1
  qmp_pointer_tap "$viewport_width" "$viewport_height" "$control_x" "$control_y" left
  if ! wait_for_guest_state "visible close control responds to QMP pointer input" 8 ssh_session \
    "hyprctl -j clients | jq -e 'all(.[]; .title != \"📰 Omarchy News Radar\")'"; then
    press esc
    return 1
  fi

  log "Driving sections, search, save, source opening, and local relevance"
  ssh_guest "cp /tmp/news-radar-fixtures/valid.json /tmp/news-radar-fixtures/current.json"
  press meta_l-alt-n
  wait_for_guest_state "valid refresh reaches current" 20 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.status == \"Current\" and .storyCount > 0'" || return 1
  wait_for_guest_state "same-origin fixture image is projected into the rendered lead" 15 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.selectedHasImage == true'" || return 1
  capture_console "success-news-radar-03-image-visible"

  log "Proving normal window management, section tabs, metrics, and local filters"
  wait_for_guest_state "Radar is an independently resizable floating client" 10 ssh_session \
    "hyprctl -j clients | jq -e 'any(.[]; .title == \"📰 Omarchy News Radar\" and .floating == true)'" || {
      ssh_session "hyprctl -j clients | jq '.[] | select(.title == \"📰 Omarchy News Radar\")'" \
        >"$RUN_DIR/news-radar-window-state-failure.json" 2>&1 || true
      ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState ''" \
        >"$RUN_DIR/news-radar-window-debug-failure.json" 2>&1 || true
      return 1
    }
  qmp '"send-key", "arguments": {"keys": [{"type":"qcode","data":"alt"},{"type":"qcode","data":"tab"}],"hold-time":3000}' >/dev/null
  wait_for_guest_state "the visible AltTab companion is presenting Radar" 5 ssh_session \
    "test \"\$(qs -p \"\$OMARCHY_PATH/shell\" ipc call omarchy-alttab openState)\" = true" || return 1
  capture_console "success-news-radar-03-companion-alttab-icon"
  wait_for_guest_state "AltTab releases cleanly back to the Radar toplevel" 10 ssh_session \
    "test \"\$(qs -p \"\$OMARCHY_PATH/shell\" ipc call omarchy-alttab openState)\" = false && hyprctl -j activewindow | jq -e '.title == \"📰 Omarchy News Radar\"'" || return 1
  window_initial_maximized="$(ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -r '.maximized'")" || return 1
  if [[ $window_initial_maximized == true ]]; then
    radar_control_geometry maximizeGeometry || return 1
    qmp_pointer_tap "$viewport_width" "$viewport_height" "$control_x" "$control_y" left
    wait_for_guest_state "initial maximized window restores through its rendered control" 10 ssh_session \
      "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.maximized == false'" || return 1
  fi
  radar_control_geometry maximizeGeometry || return 1
  qmp_pointer_tap "$viewport_width" "$viewport_height" "$control_x" "$control_y" left
  wait_for_guest_state "rendered Maximize control uses normal window state" 10 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.maximized == true and .windowVisible == true'" || return 1
  capture_console "success-news-radar-03-window-maximized"
  radar_control_geometry maximizeGeometry || return 1
  qmp_pointer_tap "$viewport_width" "$viewport_height" "$control_x" "$control_y" left
  wait_for_guest_state "rendered Restore control returns the normal window" 10 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.maximized == false'" || return 1

  window_before_width="$(ssh_session "hyprctl -j clients | jq -r '.[] | select(.title == \"📰 Omarchy News Radar\") | .size[0]'")" || return 1
  window_x="$(ssh_session "hyprctl -j clients | jq -r '.[] | select(.title == \"📰 Omarchy News Radar\") | .at[0]'")" || return 1
  window_y="$(ssh_session "hyprctl -j clients | jq -r '.[] | select(.title == \"📰 Omarchy News Radar\") | .at[1]'")" || return 1
  window_width="$window_before_width"
  window_height="$(ssh_session "hyprctl -j clients | jq -r '.[] | select(.title == \"📰 Omarchy News Radar\") | .size[1]'")" || return 1
  ssh_session "hyprctl -j clients | jq '.[] | select(.title == \"📰 Omarchy News Radar\")'" \
    >"$RUN_DIR/news-radar-window-before-resize.json" || return 1
  qmp_pointer_drag "$viewport_width" "$viewport_height" \
    "$((window_x + window_width - 3))" "$((window_y + window_height / 2))" \
    "$((window_x + window_width - 123))" "$((window_y + window_height / 2))" || return 1
  window_after_width="$(ssh_session "hyprctl -j clients | jq -r '.[] | select(.title == \"📰 Omarchy News Radar\") | .size[0]'")" || return 1
  ssh_session "hyprctl -j clients | jq '.[] | select(.title == \"📰 Omarchy News Radar\")'" \
    >"$RUN_DIR/news-radar-window-after-resize.json" || return 1
  if ((window_after_width >= window_before_width)); then
    log "Resize assertion failed: before=$window_before_width after=$window_after_width"
    return 1
  fi

  ssh_session "setsid uwsm-app -- xdg-terminal-exec --title='Radar Alt Tab Fixture' -e bash -c 'sleep 120' >/dev/null 2>&1 &" || return 1
  wait_for_guest_state "another ordinary window can take focus" 15 ssh_session \
    "hyprctl -j activewindow | jq -e '.title == \"Radar Alt Tab Fixture\"'" || return 1
  press alt-tab
  wait_for_guest_state "Alt+Tab returns focus to the Radar toplevel" 10 ssh_session \
    "hyprctl -j activewindow | jq -e '.title == \"📰 Omarchy News Radar\"'" || return 1

  press tab
  wait_for_guest_state "Tab cycles to the next section" 10 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.section == \"for-you\"'" || return 1
  press shift-tab
  wait_for_guest_state "Shift+Tab cycles to the previous section" 10 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.section == \"front-page\"'" || return 1

  press 4
  wait_for_guest_state "validated source metrics are rendered for plugin activity" 10 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.section == \"plugins\" and (.selectedMetricIds | index(\"marketplace-views\")) != null and (.selectedMetricIds | index(\"marketplace-hearts\")) != null and .selectedMarketplaceUrl == \"https://plugins.omarchy.org/plugin.html?id=io.github.mtolhuys.disk-lens\"'" || return 1
  capture_console "success-news-radar-03-metrics"
  radar_control_geometry pluginPageGeometry || return 1
  qmp_pointer_tap "$viewport_width" "$viewport_height" "$control_x" "$control_y" left
  wait_for_guest_state "plugin page opens the exact human-facing marketplace URL" 10 ssh_session \
    "test \"\$(cat \"\${XDG_STATE_HOME:-\$HOME/.local/state}/omarchy-news-radar/lab-opened-url\")\" = 'https://plugins.omarchy.org/plugin.html?id=io.github.mtolhuys.disk-lens'" || return 1
  radar_control_geometry settingsGeometry || return 1
  qmp_pointer_tap "$viewport_width" "$viewport_height" "$control_x" "$control_y" left
  wait_for_guest_state "Settings opens the current section options" 10 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.sectionSettingsOpen == true and (.sectionSources | startswith(\"Omarchy Plugin Marketplace\"))'" || return 1
  capture_console "success-news-radar-03-settings-options"

  radar_control_geometry sectionNameGeometry || return 1
  qmp_pointer_tap "$viewport_width" "$viewport_height" "$control_x" "$control_y" left
  press ctrl-a
  type_text "Extensions"
  radar_control_geometry sectionNameApplyGeometry || return 1
  qmp_pointer_tap "$viewport_width" "$viewport_height" "$control_x" "$control_y" left
  wait_for_guest_state "rendered section name persists locally" 10 ssh_session \
    "jq -e '.schemaVersion == 5 and .preferences.sectionProfiles.plugins == {name:\"Extensions\"}' \"\${XDG_STATE_HOME:-\$HOME/.local/state}/omarchy-news-radar/state.json\" && \
     ! grep -q 'BACKGROUND · THEME-DERIVED\|sectionIconSparkButton\|sectionToneAccentButton' $plugin_dir/src/Panel.qml" || return 1
  capture_console "success-news-radar-03-section-identity-fixed"
  radar_control_geometry sectionAppearanceResetGeometry || return 1
  qmp_pointer_tap "$viewport_width" "$viewport_height" "$control_x" "$control_y" left
  wait_for_guest_state "name reset restores only the selected section default" 10 ssh_session \
    "jq -e '.preferences.sectionProfiles.plugins == {name:\"Plugins\"} and .preferences.sectionProfiles.core == {name:\"Core\"}' \"\${XDG_STATE_HOME:-\$HOME/.local/state}/omarchy-news-radar/state.json\"" || return 1

  window_x="$(ssh_session "hyprctl -j clients | jq -r '.[] | select(.title == \"📰 Omarchy News Radar\") | .at[0]'")" || return 1
  window_y="$(ssh_session "hyprctl -j clients | jq -r '.[] | select(.title == \"📰 Omarchy News Radar\") | .at[1]'")" || return 1
  window_width="$(ssh_session "hyprctl -j clients | jq -r '.[] | select(.title == \"📰 Omarchy News Radar\") | .size[0]'")" || return 1
  window_height="$(ssh_session "hyprctl -j clients | jq -r '.[] | select(.title == \"📰 Omarchy News Radar\") | .size[1]'")" || return 1
  settings_center_x=$((window_x + window_width / 2))
  settings_center_y=$((window_y + window_height / 2))
  qmp_pointer_scroll_down "$viewport_width" "$viewport_height" "$settings_center_x" "$settings_center_y" 8 || return 1
  radar_control_geometry filterUnreadGeometry || return 1
  qmp_pointer_tap "$viewport_width" "$viewport_height" "$control_x" "$control_y" left
  wait_for_guest_state "rendered filter control persists only the Plugins filter" 10 ssh_session \
    "jq -e '.schemaVersion == 5 and .preferences.sectionFilters.plugins.unreadOnly == true and .preferences.sectionFilters.core.unreadOnly == false' \"\${XDG_STATE_HOME:-\$HOME/.local/state}/omarchy-news-radar/state.json\"" || return 1
  radar_control_geometry filterResetGeometry || return 1
  qmp_pointer_tap "$viewport_width" "$viewport_height" "$control_x" "$control_y" left
  wait_for_guest_state "rendered reset restores the exact section defaults" 10 ssh_session \
    "jq -e '.preferences.sectionFilters.plugins == {period:\"all\",significance:\"all\",unreadOnly:false,imagesOnly:false,types:[]}' \"\${XDG_STATE_HOME:-\$HOME/.local/state}/omarchy-news-radar/state.json\"" || return 1
  press esc
  press 1

  press 2
  wait_for_guest_state "For You matches the locally installed exact plugin id" 15 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.section == \"for-you\" and .storyCount == 2'" || return 1
  ssh_session "$helper set-preferences --interests-json '[\"notes\"]'" >"$RUN_DIR/news-radar-private-interests.json" || return 1
  press 1
  press 2
  wait_for_guest_state "private interest adds a matching real projection without leaving local state" 15 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.section == \"for-you\" and .storyCount == 3' && \
     jq -e '.preferences.interests == [\"notes\"]' \"\${XDG_STATE_HOME:-\$HOME/.local/state}/omarchy-news-radar/state.json\"" || return 1
  ssh_session "$helper set-preferences --images-visible false" >"$RUN_DIR/news-radar-images-off.json" || return 1
  press 1
  wait_for_guest_state "image-off preference preserves the complete text story" 15 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.storyCount > 0 and .selectedHasImage == false'" || return 1
  capture_console "success-news-radar-03-image-off"
  ssh_session "$helper set-preferences --images-visible true" >"$RUN_DIR/news-radar-images-on.json" || return 1
  press 2
  press j
  wait_for_guest_state "j selects the next story" 10 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.selectedIndex == 1'" || return 1
  press k
  press 4
  wait_for_guest_state "numeric section key switches to Plugins" 10 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.section == \"plugins\" and .storyCount == 3'" || return 1
  press slash
  type_text "Workspace"
  wait_for_guest_state "search narrows the validated local projection" 10 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.storyCount == 1 and .selectedTitle == \"Workspace Notes joined the marketplace\"'" || return 1
  press esc
  wait_for_guest_state "Escape returns search focus to panel navigation" 10 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.searchFocused == false'" || return 1
  press s
  wait_for_guest_state "save writes bounded local metadata" 10 ssh_session \
    "jq -e '.saved | has(\"evt_53642b4d3e0e59c943494606\")' \"\${XDG_STATE_HOME:-\$HOME/.local/state}/omarchy-news-radar/state.json\"" || return 1
  press o
  wait_for_guest_state "source opening reaches the inert shim with the exact HTTPS URL" 10 ssh_session \
    "test \"\$(cat \"\${XDG_STATE_HOME:-\$HOME/.local/state}/omarchy-news-radar/lab-opened-url\")\" = https://github.com/example/omarchy-notes" || return 1
  press slash
  press ctrl-a
  press backspace
  press esc
  capture_console "success-news-radar-03-keyboard-source-save"

  log "Proving the rendered session cutoff across an in-session refresh"
  ssh_guest "cp /tmp/news-radar-fixtures/later.json /tmp/news-radar-fixtures/current.json"
  press r
  wait_for_guest_state "new event arrives without changing the open session cutoff" 15 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.status == \"Current\" and .sessionThrough == \"2026-08-31T14:00:00Z\"'" || return 1
  press esc
  wait_for_guest_state "normal close advances seen state only to the captured cutoff" 15 ssh_session \
    "jq -e '.seenThrough == \"2026-08-31T14:00:00Z\"' \"\${XDG_STATE_HOME:-\$HOME/.local/state}/omarchy-news-radar/state.json\"" || return 1
  press meta_l-alt-n
  wait_for_guest_state "the next panel session is current and ready for navigation" 15 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.opened == true and .status == \"Current\" and .searchFocused == false'" || return 1
  press 2
  wait_for_guest_state "event introduced during the prior session remains new" 15 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.section == \"for-you\" and .selectedTitle == \"An event that arrived during the open session\" and .selectedIsNew == true'" || return 1

  log "Proving malformed, oversized, partial, offline, empty, long, and dense states"
  ssh_guest "cp /tmp/news-radar-fixtures/malformed.json /tmp/news-radar-fixtures/current.json"
  press r
  wait_for_guest_state "malformed candidate is rejected with cache intact" 15 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.status == \"Invalid feed\" and .storyCount > 0'" || return 1
  capture_console "success-news-radar-04-invalid-feed"
  ssh_guest "cp /tmp/news-radar-fixtures/oversized.json /tmp/news-radar-fixtures/current.json"
  press r
  wait_for_guest_state "oversized candidate is rejected with cache intact" 15 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.status == \"Invalid feed\" and .storyCount > 0'" || return 1
  ssh_guest "cp /tmp/news-radar-fixtures/partial.json /tmp/news-radar-fixtures/current.json"
  press r
  wait_for_guest_state "partial source health remains a usable edition" 15 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.status == \"Source partial\" and .storyCount > 0'" || return 1
  capture_console "success-news-radar-05-source-partial"
  ssh_guest "rm -f /tmp/news-radar-fixtures/current.json"
  press r
  wait_for_guest_state "offline refresh preserves the partial last-known-good edition" 15 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.status == \"Offline\" and .storyCount > 0'" || return 1
  capture_console "success-news-radar-06-offline"
  ssh_guest "cp /tmp/news-radar-fixtures/empty.json /tmp/news-radar-fixtures/current.json"
  press r
  press 5
  wait_for_guest_state "empty valid edition has a visible empty state" 15 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.status == \"Current\" and .section == \"community\" and .storyCount == 0 and (.emptyStateMessage | contains(\"Everyone reading this edition gets the same selection\"))'" || return 1
  capture_console "success-news-radar-07-community-empty-explained"
  ssh_guest "cp /tmp/news-radar-fixtures/dense.json /tmp/news-radar-fixtures/current.json"
  press r
  press 4
  wait_for_guest_state "dense projection starts with one bounded page" 15 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.status == \"Current\" and .storyCount == 12 and .totalStories == 120 and .hasMoreStories == true'" || return 1
  shell_rss_open="$(ssh_session "ps -o rss= -p \"\$(pgrep -n -u \"\$USER\" quickshell)\" | tr -d ' '")"
  projection_seconds="$(ssh_session "TIMEFORMAT='%R'; { time $helper project --section plugins --installed-json '[]' --query '' --limit 120 >/dev/null; } 2>/tmp/news-radar-projection.time && cat /tmp/news-radar-projection.time")" || return 1
  dense_started_ms="$(date +%s%3N)"
  press end
  radar_control_geometry loadMoreGeometry || return 1
  qmp_pointer_tap "$viewport_width" "$viewport_height" "$control_x" "$control_y" left
  wait_for_guest_state "rendered Load more reveals the next finite page" 10 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.storyCount == 24 and .totalStories == 120 and .hasMoreStories == true'" || return 1
  dense_ready_ms="$(date +%s%3N)"
  capture_console "success-news-radar-08-dense"
  # The load-more click leaves the synthetic pointer over the story list. Move
  # it off the Radar before replacing the model so hover selection cannot race
  # the keyboard's explicit Home selection.
  qmp_pointer_move "$viewport_width" "$viewport_height" 4 4 || return 1
  ssh_guest "cp /tmp/news-radar-fixtures/long.json /tmp/news-radar-fixtures/current.json"
  press r
  wait_for_guest_state "long-content edition refresh completes" 15 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.status == \"Current\" and .storyCount > 0'" || return 1
  press 2
  press home
  wait_for_guest_state "long Unicode story renders as plain text" 15 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.section == \"for-you\" and .selectedIndex == 0 and (.selectedTitle | startswith(\"長い見出し\"))'" || return 1

  log "Reviewing light, dark, narrow, 200 percent text, and reduced-motion checkpoints"
  ssh_session "omarchy-theme-set catppuccin-latte >/dev/null"
  capture_console "success-news-radar-09-light-long"
  ssh_session "omarchy-theme-set tokyo-night >/dev/null"
  capture_console "success-news-radar-10-dark-long"
  ssh_session "mkdir -p \"\$HOME/.config/omarchy\" && printf '[font]\nbase-size = 24\n' >\"\$HOME/.config/omarchy/shell.toml\""
  capture_console "success-news-radar-11-text-200"
  monitor_name="$(ssh_session "hyprctl -j monitors | jq -r '.[0].name'")"
  ssh_session "hyprctl keyword monitor '$monitor_name,1366x768@60,0x0,1' >/dev/null && hyprctl keyword animations:enabled false >/dev/null"
  capture_console "success-news-radar-12-narrow-reduced-motion"
  close_started_ms="$(date +%s%3N)"
  press esc
  wait_for_guest_state "close tears down every owned helper" 15 ssh_session \
    "hyprctl -j clients | jq -e 'all(.[]; .title != \"📰 Omarchy News Radar\")' && ! pgrep -u \"\$USER\" -f '[/]bin/news-radar-client'" || return 1
  close_ready_ms="$(date +%s%3N)"
  shell_rss_closed="$(ssh_session "ps -o rss= -p \"\$(pgrep -n -u \"\$USER\" quickshell)\" | tr -d ' '")"
  [[ $projection_seconds =~ ^[0-9]+([.][0-9]+)?$ ]] || return 1
  [[ $shell_rss_open =~ ^[0-9]+$ && $shell_rss_closed =~ ^[0-9]+$ ]] || return 1
  jq -n \
    --argjson openLatencyMs "$((open_ready_ms - open_started_ms))" \
    --argjson denseEndLatencyMs "$((dense_ready_ms - dense_started_ms))" \
    --argjson closeTeardownMs "$((close_ready_ms - close_started_ms))" \
    --arg projectionSeconds "$projection_seconds" \
    --argjson shellRssOpenKiB "$shell_rss_open" \
    --argjson shellRssClosedKiB "$shell_rss_closed" \
    '{context:"disposable Plugin Lab VM; shared shell RSS is observational, not plugin-exclusive", openLatencyMs:$openLatencyMs, projection120Seconds:($projectionSeconds|tonumber), denseLoadMoreLatencyMs:$denseEndLatencyMs, closeTeardownMs:$closeTeardownMs, helperProcessesAfterClose:0, shellRssOpenKiB:$shellRssOpenKiB, shellRssClosedKiB:$shellRssClosedKiB}' \
    >"$RUN_DIR/news-radar-performance.json" || return 1

  log "Proving same-path runtime replacement and clean lifecycle removal"
  before_change_count="$(ssh_session "journalctl --user -t omarchy-shell --since '@$start_epoch' --no-pager | grep -Fc 'Local plugin changed, reloading: io.github.mtolhuys.news-radar' || true")"
  ssh_session "sed -i 's/news-radar-0.1.0+identity-2/news-radar-0.1.0+identity-3/' $plugin_dir/src/Panel.qml"
  wait_for_guest_state "shell observes the same-path candidate update" 20 ssh_session \
    "test \"\$(journalctl --user -t omarchy-shell --since '@$start_epoch' --no-pager | grep -Fc 'Local plugin changed, reloading: io.github.mtolhuys.news-radar' || true)\" -gt '$before_change_count'" || return 1
  ssh_session "omarchy-shell shell toggle io.github.mtolhuys.news-radar '{}'"
  wait_for_guest_state "same-path panel update replaces the live runtime identity" 20 ssh_session \
    "test \"\$(omarchy-shell shell call io.github.mtolhuys.news-radar runtimeIdentity '')\" = news-radar-0.1.0+identity-3" || return 1
  capture_console "success-news-radar-13-hot-update"
  press esc
  ssh_session "$shortcut remove" >"$RUN_DIR/news-radar-shortcut-removed.json" || return 1
  ssh_session "! grep -F -- '-- BEGIN OMARCHY NEWS RADAR MANAGED SHORTCUT' \"\$HOME/.config/hypr/bindings.lua\" && \
    test -z \"\$(hyprctl configerrors)\" && \
    hyprctl binds -j | jq -e '[.[] | select(((.key // \"\") | ascii_upcase) == \"N\" and .modmask == 72)] | length == 0' && \
    hyprctl binds -j | jq -e '[.[] | select((.description // \"\") == \"Editor\" and ((.key // \"\") | ascii_upcase) == \"N\" and .modmask == 65)] | length == 1'" || return 1
  ssh_session "omarchy-plugin-disable io.github.mtolhuys.news-radar"
  wait_for_guest_state "disable unloads runtime but preserves local state" 15 ssh_session \
    "omarchy-plugin-list --json | jq -e 'any(.[]; .id == \"io.github.mtolhuys.news-radar\" and .enabled == false)' && test -f \"\${XDG_STATE_HOME:-\$HOME/.local/state}/omarchy-news-radar/state.json\"" || return 1
  ssh_session "omarchy-plugin-enable io.github.mtolhuys.news-radar"
  wait_for_guest_state "re-enable restores candidate discovery" 15 ssh_session \
    "omarchy-plugin-list --json | jq -e 'any(.[]; .id == \"io.github.mtolhuys.news-radar\" and .enabled == true)'" || return 1
  ssh_session "$launcher remove" >"$RUN_DIR/news-radar-launcher-removed.json" || return 1
  wait_for_guest_state "launcher helper removes only its receipt-backed files" 15 ssh_session \
    "$launcher status | jq -e '.state == \"absent\" and .installed == false' && \
     test ! -e \"\${XDG_DATA_HOME:-\$HOME/.local/share}/applications/io.github.mtolhuys.news-radar.desktop\" && \
     test ! -e \"\${XDG_DATA_HOME:-\$HOME/.local/share}/icons/hicolor/scalable/apps/io.github.mtolhuys.news-radar.svg\"" || return 1
  press meta_l-spc
  wait_for_guest_state "Omarchy menu reopens after launcher removal" 10 ssh_session \
    "hyprctl -j layers | jq -e '[.. | objects | select(.namespace? == \"omarchy-menu\")] | length >= 1'" || return 1
  type_text "omarchy news radar"
  sleep 1
  capture_console "success-news-radar-14-app-launcher-removed"
  press ret
  sleep 1
  ssh_session "hyprctl -j clients | jq -e 'all(.[]; .title != \"📰 Omarchy News Radar\")'" || return 1
  press esc
  ssh_session "omarchy-plugin-remove io.github.mtolhuys.news-radar --yes"
  wait_for_guest_state "plugin removal unloads files and preserves user state" 15 ssh_session \
    "test ! -e \"\$HOME/.config/omarchy/plugins/io.github.mtolhuys.news-radar\" && test -f \"\${XDG_STATE_HOME:-\$HOME/.local/state}/omarchy-news-radar/state.json\" && omarchy-plugin-list --json | jq -e 'all(.[]; .id != \"io.github.mtolhuys.news-radar\")'" || return 1
  ssh_session "omarchy-plugin-remove io.github.mtolhuys.disk-lens --yes" >/dev/null || return 1
  ssh_session "omarchy-plugin-remove vbrosseau.alttab --yes && omarchy-plugin-remove omadock --yes" >/dev/null || return 1
  ssh_session "journalctl --user --since '@$start_epoch' --no-pager" >"$RUN_DIR/news-radar-user-journal.log" || true
  if grep -E 'io\.github\.mtolhuys\.news-radar.*(failed to load|ReferenceError|TypeError)|(Panel|BarWidget)\.qml.*(error|Error)' \
    "$RUN_DIR/news-radar-user-journal.log"; then
    echo "News Radar runtime errors were present in the guest journal" >&2
    return 1
  fi
  ssh_session "test -z \"\$(hyprctl configerrors)\" && ! pgrep -u \"\$USER\" -f '[/]bin/news-radar-client'" || return 1
  ssh_guest "systemctl --user stop omarchy-news-radar-fixture.service 2>/dev/null || true"
  capture_console "success-news-radar-14-shortcut-removed-editor-intact"

  printf 'ok - exact candidate passed app launcher, newspaper, images, interests, shortcut, cached-first, keyboard, pointer, source, state, failure, visual, update, and lifecycle assertions\n'
}
