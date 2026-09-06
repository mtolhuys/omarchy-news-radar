#!/bin/bash

# Opening, discovery, and empty-view acceptance proof. Only the disposable guest receives
# window rules, plugin activation, fixtures, or keyboard and pointer events.
# Shared setup helpers include indirect callbacks used by the harness.
# shellcheck disable=SC2329

omarchy_host_test() {
  local product_root lab_root start_epoch runtime_identity neighbor_number neighbor_title neighbor_address
  local plugin_dir viewport_width viewport_height saved_geometry selected_before state_before _card_step collection_id project_id project_name source_label source_focus geometry_before geometry_after
  local scenario_root=/tmp/news-radar-briefing
  local scenario_state=/tmp/news-radar-briefing/xdg-state/omarchy-news-radar/state.json
  product_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
  lab_root="$(cd -- "$product_root/../../omarchy/plugin-lab" && pwd)"
  # shellcheck source=/dev/null
  source "$lab_root/host-tests/helpers/pointer.sh"
  # shellcheck source=/dev/null
  source "$product_root/tests/lab/pointer.sh"
  # The disposable guest expands this path, never the host.
  # shellcheck disable=SC2016
  plugin_dir='$HOME/.config/omarchy/plugins/io.github.mtolhuys.news-radar'
  runtime_identity="$(sed -n 's/.*property string runtimeBuildIdentity: "\([^"]*\)".*/\1/p' "$product_root/src/Panel.qml")"
  [[ $runtime_identity =~ ^news-radar-[0-9]+\.[0-9]+\.[0-9]+\+identity-2$ ]] || return 1
  start_epoch="$(date +%s)"

  briefing_wait() {
    local label="$1" predicate="$2"
    wait_for_guest_state "$label" 20 ssh_session \
      "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '$predicate'"
  }

  briefing_capture() {
    local name="$1"
    ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState ''" \
      >"$RUN_DIR/briefing-$name.json" || return 1
    capture_console "success-briefing-$name"
  }

  briefing_key() {
    local name="$1" key="$2" predicate="$3"
    press "$key"
    ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState ''" \
      >"$RUN_DIR/briefing-key-$name.json" || return 1
    if ! briefing_wait "keyboard focus after $name stays in the intended briefing control" "$predicate"; then
      ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState ''" \
        >"$RUN_DIR/briefing-key-$name-failed.json" || true
      capture_console "failure-briefing-key-$name"
      return 1
    fi
    ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState ''" \
      >"$RUN_DIR/briefing-key-$name.json"
  }

  # Called indirectly by the bounded wait helper.
  # Older ShellCheck reports SC2317 for these harness callbacks/helpers.
  # shellcheck disable=SC2317,SC2329
  briefing_choices_fit() {
    local name="$1" window geometry method
    window="$(ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState ''" \
      | awk '/^\{.*\}$/ { value = $0 } END { print value }')" || return 1
    for method in startTodayGeometry browseStoriesGeometry; do
      geometry="$(ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar '$method' ''" \
        | awk '/^\{.*\}$/ { value = $0 } END { print value }')" || return 1
      printf '%s\n' "$geometry" >"$RUN_DIR/briefing-$name-$method.json"
      jq -e --argjson window "$window" \
        '.visible == true and .width > 0 and .height > 0 and .x >= 0 and .y >= 0 and
         (.x + .width) <= ($window.windowWidth + 1) and (.y + .height) <= ($window.windowHeight + 1)' \
        <<<"$geometry" >/dev/null || return 1
    done
  }

  # Called indirectly by the bounded wait helper.
  # Older ShellCheck reports SC2317 for these harness callbacks/helpers.
  # shellcheck disable=SC2317,SC2329
  briefing_frame_fits() {
    local frame
    frame="$(ssh_session "hyprctl -j clients | jq '[.[] | select(.title == \"📰 Omarchy News Radar\") | {title,at,size}]'")" || return 1
    printf '%s\n' "$frame" >"$RUN_DIR/briefing-frame.json"
    jq -e --argjson width "$viewport_width" --argjson height "$viewport_height" \
      'length == 1 and all(.[]; .at[0] >= 0 and .at[1] >= 0 and
       (.at[0] + .size[0]) <= $width and (.at[1] + .size[1]) <= $height)' \
      <<<"$frame" >/dev/null
  }

  # Retained geometry helper; not called by this focused scenario.
  # shellcheck disable=SC2317
  briefing_control_fits() {
    local method="$1" geometry window
    geometry="$(ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar '$method' ''")" || return 1
    window="$(ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState ''")" || return 1
    printf '%s\n' "$geometry" >"$RUN_DIR/briefing-text-200-$method.json"
    jq -e --argjson window "$window" \
      '.visible == true and .width > 0 and .height > 0 and .x >= 0 and .y >= 0 and
       (.x + .width) <= ($window.windowWidth + 1) and (.y + .height) <= ($window.windowHeight + 1)' \
      <<<"$geometry" >/dev/null
  }

  briefing_click() {
    local method="$1" geometry position window_x window_y local_x local_y
    ssh_session "hyprctl -j activewindow | jq -e '.title == \"📰 Omarchy News Radar\"'" >/dev/null || return 1
    geometry="$(ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar '$method' ''" \
      | awk '/^\{.*\}$/ { value = $0 } END { print value }')" || return 1
    printf '%s\n' "$geometry" >"$RUN_DIR/briefing-$method.json"
    jq -e '.visible == true and .width > 0 and .height > 0 and .x >= 0 and .y >= 0' <<<"$geometry" >/dev/null || return 1
    position="$(ssh_session "hyprctl -j clients | jq -r '.[] | select(.title == \"📰 Omarchy News Radar\") | [.at[0], .at[1]] | @tsv'")" || return 1
    read -r window_x window_y <<<"$position"
    local_x="$(jq -r '(.x + .width / 2) | floor' <<<"$geometry")"
    local_y="$(jq -r '(.y + .height / 2) | floor' <<<"$geometry")"
    radar_pointer_tap "$viewport_width" "$viewport_height" "$((window_x + local_x))" "$((window_y + local_y))" left
  }

  opening_focus_detail() {
    local wanted="$1" _attempt current
    for _attempt in {1..24}; do
      current="$(ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -r '.insightDetailFocusedControl'")" || return 1
      [[ $current != "$wanted" ]] || return 0
      press tab
    done
    briefing_capture failed-detail-focus
    return 1
  }

  # A cache-file notification can queue another local projection just after
  # the refresh flag clears. Press Enter only after the rendered choice has
  # stayed enabled across the complete helper pipeline.
  # Called indirectly by wait_for_guest_state.
  # shellcheck disable=SC2317
  opening_choice_idle() {
    local _sample
    for _sample in {1..5}; do
      ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.onboardingVisible == true and .windowVisible == true and .openingPhase == \"visible\" and .helperRunning == false and .briefingBusy == false and .pendingProjection == false'" >/dev/null || return 1
      sleep 0.25
    done
  }

  opening_empty_keys() {
    state_before="$(ssh_guest "sha256sum $scenario_state")" || return 1
    press s
    press u
    press o
    press a
    briefing_wait "empty view keeps read, save, and source actions inactive" \
      '.readerActionsEnabled == false and .inspectorVisible == false and .helperRunning == false and .opened == true' || return 1
    [[ "$(ssh_guest "sha256sum $scenario_state")" == "$state_before" ]]
  }

  briefing_open() {
    local geometry previous="" stable=0 bar_x bar_y _attempt
    for _attempt in {1..12}; do
      geometry="$(ssh_session "omarchy-shell shell debugBarGeometry" | jq -c '[.[] | select(.id == "io.github.mtolhuys.news-radar")]')" || return 1
      printf '%s\n' "$geometry" >"$RUN_DIR/opening-bar-before.json"
      if [[ $geometry == "$previous" ]] && jq -e 'length == 1 and .[0].visible == true and .[0].width > 0 and .[0].height > 0' <<<"$geometry" >/dev/null; then
        stable=$((stable + 1))
        ((stable < 3)) || break
      else stable=0; fi
      previous="$geometry"
      sleep 0.25
    done
    ((stable >= 3)) || return 1
    bar_x="$(jq -r '.[] | select(.id == "io.github.mtolhuys.news-radar" and .visible == true) | (.x + .width / 2) | floor' <<<"$geometry")"
    bar_y="$(jq -r '.[] | select(.id == "io.github.mtolhuys.news-radar" and .visible == true) | (.y + .height / 2) | floor' <<<"$geometry")"
    [[ $bar_x =~ ^[0-9]+$ && $bar_y =~ ^[0-9]+$ ]] || return 1
    radar_pointer_tap "$viewport_width" "$viewport_height" "$bar_x" "$bar_y" left || return 1
    if ! briefing_wait "newspaper opens the exact candidate window" \
      ".opened == true and .windowVisible == true and .build == \"$runtime_identity\" and .localStateReady == true"; then
      ssh_session "journalctl --user --since '@$start_epoch' --no-pager" >"$RUN_DIR/failed-opening-journal.log" || true
      ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState ''" >"$RUN_DIR/failed-opening-state.json" 2>&1 || true
      ssh_session "hyprctl -j clients" >"$RUN_DIR/failed-opening-clients.json" || true
      ssh_session "omarchy-shell shell debugBarGeometry" >"$RUN_DIR/failed-opening-bar.json" || true
      capture_console failed-opening
      return 1
    fi
  }

  briefing_close() {
    press esc
    wait_for_guest_state "Escape closes the panel and its helpers" 15 ssh_session \
      "hyprctl -j clients | jq -e 'all(.[]; .title != \"📰 Omarchy News Radar\")' && ! pgrep -u \"\$USER\" -f '([/]bin/news-radar-client|[r]adar[.]cli_client)'"
  }

  briefing_resize() {
    local width="$1" height="$2"
    ssh_session "hyprctl -j clients | jq -e '[.[] | select(.title == \"📰 Omarchy News Radar\")] | length == 1'" >/dev/null || return 1
    ssh_session "hyprctl -j clients | jq '.[] | select(.title == \"📰 Omarchy News Radar\") | {address,at,size,title}'" \
      >"$RUN_DIR/briefing-resize-before-${width}x${height}.json" || return 1
    ssh_session "hyprctl dispatch 'hl.dsp.window.resize({ window = \"title:📰 Omarchy News Radar\", x = $width, y = $height })' >/dev/null && \
      hyprctl dispatch 'hl.dsp.window.move({ window = \"title:📰 Omarchy News Radar\", x = 20, y = 50 })' >/dev/null" || return 1
    briefing_wait "window reaches the requested ${width}x${height} layout" \
      ".windowWidth == $width and .windowHeight == $height and .windowVisible == true"
  }

  opening_neighbors_unchanged() {
    local current
    current="$(ssh_session "hyprctl -j clients | jq -c '[.[] | select(.title == \"Radar Opening Neighbor\" or .title == \"Radar Opening Neighbor 2\" or .title == \"Radar Opening Neighbor 3\") | {address,title,at,size}] | sort_by(.address)'")" || return 1
    jq -e --argjson current "$current" '. == $current' "$RUN_DIR/opening-neighbor-before.json" >/dev/null
  }

  opening_window_evidence() {
    local name="$1"
    ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState ''" >"$RUN_DIR/$name-state.json" || true
    ssh_session "hyprctl -j clients" >"$RUN_DIR/$name-clients.json" || true
    ssh_session "$plugin_dir/bin/news-radar-client window-state" >"$RUN_DIR/$name-native.json" 2>&1 || true
    capture_console "$name"
  }

  opening_motion_start() {
    local name="$1"
    ssh_session "python3 $scenario_root/candidate/tests/lab/sample_opening.py $scenario_root/$name >$scenario_root/$name.log 2>&1 &"
  }

  opening_motion_finish() {
    local name="$1"
    wait_for_guest_state "bounded $name sampling completes" 12 ssh_guest "test -f $scenario_root/$name/done" || return 1
    mkdir -p "$RUN_DIR/$name"
    ssh_guest "tar -C $scenario_root/$name -cf - ." | tar -C "$RUN_DIR/$name" -xf - || return 1
    ssh_session "hyprctl -j monitors" >"$RUN_DIR/$name/monitors.json" || return 1
    jq -e --slurpfile expected "$RUN_DIR/opening-neighbor-before.json" --slurpfile monitors "$RUN_DIR/$name/monitors.json" '
      any(.[]; (.radar | length) == 1) and
      all(.[]; (.radar | length) <= 1 and
        ([.neighbor[] | {address,title,at,size}] | sort_by(.address)) == $expected[0] and
        all(.radar[]; . as $window | [$monitors[0][] | select(.id == $window.monitor)][0] as $monitor |
          .floating == true and .at[0] >= ($monitor.x + $monitor.reserved[0]) and .at[1] >= ($monitor.y + $monitor.reserved[1]) and
          (.at[0] + .size[0]) <= ($monitor.x + $monitor.width / $monitor.scale - $monitor.reserved[2]) and
          (.at[1] + .size[1]) <= ($monitor.y + $monitor.height / $monitor.scale - $monitor.reserved[3])))' \
      "$RUN_DIR/$name/samples.json" >/dev/null
  }

  log "Staging only Radar and isolating the fixture feed and local reader state"
  tar -C "$product_root" --exclude=.git --exclude=dist --exclude='__pycache__' -cf - . | ssh_guest \
    "mkdir -p $scenario_root/candidate && tar -C $scenario_root/candidate -xf -" || return 1
  git -C "$product_root" rev-parse HEAD >"$RUN_DIR/briefing-source-head.txt"
  git -C "$product_root" status --short >"$RUN_DIR/briefing-source-status.txt"
  ssh_guest "git -C $scenario_root/candidate init -q && git -C $scenario_root/candidate add . && \
    git -C $scenario_root/candidate -c user.name=PluginLab -c user.email=lab@invalid commit -qm candidate && \
    python3 $scenario_root/candidate/tests/lab/prepare_briefing_fixtures.py \
      $scenario_root/candidate/tests/fixtures/feed-valid.json $scenario_root/fixtures && \
    cp $scenario_root/fixtures/initial.json $scenario_root/fixtures/current.json && \
    mkdir -m 700 $scenario_root/xdg-state $scenario_root/xdg-cache && \
    systemd-run --user --unit=news-radar-briefing-fixture --collect --quiet -- \
      python3 $scenario_root/candidate/tests/lab/fixture_server.py --port 18765 --directory $scenario_root/fixtures" || return 1
  wait_for_guest_state "isolated loopback edition is ready" 10 ssh_guest \
    "curl -fsS http://127.0.0.1:18765/current.json >/dev/null" || return 1
  ssh_session "mkdir -p \"\$HOME/.local/bin\" && \
    cp $scenario_root/candidate/tests/lab/fixtures/xdg-open \"\$HOME/.local/bin/xdg-open\" && \
    chmod +x \"\$HOME/.local/bin/xdg-open\" && \
    cp \"\$HOME/.config/hypr/bindings.lua\" $scenario_root/bindings.before && \
    printf '%s\n' \
      'hl.env(\"OMARCHY_NEWS_RADAR_TEST_MODE\", \"1\")' \
      'hl.env(\"OMARCHY_NEWS_RADAR_TEST_INSIGHTS\", \"$scenario_root/candidate/tests/fixtures/insights-valid.json\")' \
      'hl.env(\"OMARCHY_NEWS_RADAR_TEST_FEED_URL\", \"http://127.0.0.1:18765/current.json\")' \
      'hl.env(\"OMARCHY_NEWS_RADAR_TEST_TIMEOUT_SECONDS\", \"5\")' \
      'hl.env(\"XDG_STATE_HOME\", \"$scenario_root/xdg-state\")' \
      'hl.env(\"XDG_CACHE_HOME\", \"$scenario_root/xdg-cache\")' \
      'hl.env(\"PATH\", os.getenv(\"HOME\") .. \"/.local/bin:\" .. (os.getenv(\"PATH\") or \"/usr/bin\"))' \
      >>\"\$HOME/.config/hypr/bindings.lua\" && \
    hyprctl reload >/dev/null && test -z \"\$(hyprctl configerrors)\" && omarchy-restart-shell" || return 1
  wait_for_guest_state "shell has the isolated fixture environment" 30 ssh_session \
    "omarchy-shell shell ping >/dev/null" || return 1
  ssh_session "omarchy-plugin-add $scenario_root/candidate --enable --yes" >"$RUN_DIR/briefing-install.log" || return 1
  wait_for_guest_state "candidate is installed and its newspaper is reachable" 20 ssh_session \
    "omarchy-plugin-list --json | jq -e 'any(.[]; .id == \"io.github.mtolhuys.news-radar\" and .enabled == true)' && \
     omarchy-shell shell debugBarGeometry | jq -e 'any(.[]; .id == \"io.github.mtolhuys.news-radar\" and .visible == true)'" || return 1
  ssh_session "git -C $plugin_dir rev-parse HEAD" >"$RUN_DIR/briefing-installed-head.txt" || return 1
  ssh_guest "git -C $scenario_root/candidate rev-parse HEAD" >"$RUN_DIR/briefing-staged-head.txt" || return 1
  cmp "$RUN_DIR/briefing-installed-head.txt" "$RUN_DIR/briefing-staged-head.txt" || return 1
  viewport_width="$(ssh_session "hyprctl -j monitors | jq -r '.[0].width'")"
  viewport_height="$(ssh_session "hyprctl -j monitors | jq -r '.[0].height'")"
  ssh_session "omarchy-theme-set matte-black >/dev/null" || return 1

  log "Warm validated local fixtures before the first visible map"
  ssh_session "$plugin_dir/bin/news-radar-client refresh && $plugin_dir/bin/news-radar-client insights-refresh" >"$RUN_DIR/opening-cache.json" || return 1
  for neighbor_number in 1 2 3; do
    neighbor_title="Radar Opening Neighbor"
    [[ $neighbor_number == 1 ]] || neighbor_title="$neighbor_title $neighbor_number"
    ssh_session "setsid uwsm-app -- xdg-terminal-exec --title='$neighbor_title' -e bash -c 'printf \"Normal application $neighbor_number stays open during Radar testing.\\n\"; sleep 900' >/dev/null 2>&1 &" || return 1
    wait_for_guest_state "ordinary neighbor $neighbor_number is mapped" 15 ssh_session \
      "hyprctl -j clients | jq -e 'any(.[]; .title == \"$neighbor_title\" and .mapped == true)'" || return 1
  done
  ssh_session "hyprctl -j clients | jq '[.[] | select(.title == \"Radar Opening Neighbor\" or .title == \"Radar Opening Neighbor 2\" or .title == \"Radar Opening Neighbor 3\") | {address,title,at,size}] | sort_by(.address)'" >"$RUN_DIR/opening-neighbor-before.json" || return 1
  jq -e 'length == 3' "$RUN_DIR/opening-neighbor-before.json" >/dev/null || return 1
  ssh_session "hyprctl -j activewindow" >"$RUN_DIR/opening-focus-before.json" || return 1
  capture_console opening-three-applications-before
  opening_motion_start opening-motion || return 1
  briefing_open || return 1
  opening_motion_finish opening-motion || return 1
  jq -e '.localStateReady == true and .storyCount > 0 and .onboardingVisible == true' "$RUN_DIR/opening-motion/first-map-state.json" >/dev/null || return 1
  wait_for_guest_state "first-use choice is stable before activation" 20 opening_choice_idle || return 1
  briefing_key browse ret '.homeVisible == true and .onboardingVisible == false and .insightsStatus == "cached" and .homeCards >= 5' || return 1
  sleep 1
  ssh_guest "jq -e '(.readOverrides | length) == 0' $scenario_state" >/dev/null || return 1
  briefing_capture opening-01-home || return 1

  log "A repeated newspaper summon preserves focused control context"
  briefing_key home-focus f6 '.briefingControlsMode == true and .briefingFocusedControl != ""' || return 1
  selected_before="$(ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -r '.briefingFocusedControl'")"
  briefing_open || return 1
  briefing_wait "summon retains the same active home control" \
    ".briefingFocusedControl == \"$selected_before\" and .homeVisible == true" || return 1
  press f6
  ssh_session "$plugin_dir/bin/news-radar-shortcut install" >"$RUN_DIR/opening-shortcut-install.json" || return 1
  opening_motion_start opening-shortcut-summon || return 1
  press meta_l-alt-n
  briefing_wait "shortcut raises the existing normal window" '.windowVisible == true and .helperRunning == false' || return 1
  opening_motion_finish opening-shortcut-summon || return 1
  saved_geometry="$(ssh_session "hyprctl -j clients | jq -c '.[] | select(.title == \"📰 Omarchy News Radar\") | {at,size}'")" || return 1
  briefing_click maximizeGeometry || return 1
  if ! wait_for_guest_state "Maximize changes the actual compositor mode" 15 ssh_session \
    "hyprctl -j clients | jq -e 'any(.[]; .title == \"📰 Omarchy News Radar\" and .fullscreen == 1)'"; then
    opening_window_evidence failed-native-maximize
    return 1
  fi
  opening_window_evidence native-maximize
  briefing_wait "native maximize state and control settle" ' .maximized == true and .helperRunning == false' || return 1
  opening_neighbors_unchanged || return 1
  briefing_capture opening-native-maximized || return 1
  briefing_click maximizeGeometry || return 1
  if ! wait_for_guest_state "Restore recovers its normal frame with three apps untouched" 15 ssh_session \
    "hyprctl -j clients | jq -e --argjson expected '$saved_geometry' '.[] | select(.title == \"📰 Omarchy News Radar\") | .fullscreen == 0 and {at,size} == \$expected'"; then
    opening_window_evidence failed-native-restore
    return 1
  fi
  opening_window_evidence native-restore
  opening_neighbors_unchanged || return 1

  log "Reader entry is explicit and remembered window placement survives close"
  briefing_key read-first ret '.homeVisible == false and .selectedIsUnread == false and .storyCount > 0' || return 1
  briefing_resize 900 660 || return 1
  ssh_session "hyprctl dispatch 'hl.dsp.window.move({ window = \"title:📰 Omarchy News Radar\", x = 70, y = 80 })' >/dev/null" || return 1
  saved_geometry="$(ssh_session "hyprctl -j clients | jq -c '.[] | select(.title == \"📰 Omarchy News Radar\") | {at,size}'")" || return 1
  briefing_close || return 1
  opening_neighbors_unchanged || return 1
  ssh_guest "test -f $scenario_root/xdg-state/omarchy-news-radar/window.json" || return 1
  opening_motion_start opening-shortcut-reopen || return 1
  press meta_l-alt-n
  briefing_wait "shortcut reopens Radar among the same three apps" '.windowVisible == true and .helperRunning == false' || return 1
  opening_motion_finish opening-shortcut-reopen || return 1
  wait_for_guest_state "reopen restores the same moved and resized frame" 15 ssh_session \
    "hyprctl -j clients | jq -e --argjson expected '$saved_geometry' '.[] | select(.title == \"📰 Omarchy News Radar\") | {at,size} == \$expected'" || return 1
  briefing_capture opening-02-restored-home || return 1

  log "Discovery detail exposes local choices and original release sources"
  briefing_key discovery-end end '.homeVisible == true and .selectedHomeCard == (.homeCards - 1)' || return 1
  briefing_key project-open ret '.insightDetailVisible == true and .insightDetailId == "org.example.notes"' || return 1
  briefing_capture opening-03-project-detail || return 1
  opening_focus_detail plugin:org.example.notes:follow || return 1
  briefing_key follow-project ret '.insightDetailVisible == true and any(.relevanceControls[]; .kind == "plugin" and .id == "org.example.notes" and .followed == true)' || return 1
  opening_focus_detail plugin:org.example.notes:mute || return 1
  briefing_key mute-project ret '.insightDetailVisible == true and any(.relevanceControls[]; .kind == "plugin" and .id == "org.example.notes" and .muted == true and .followed == false)' || return 1
  opening_focus_detail plugin:org.example.notes:mute || return 1
  briefing_key clear-mute ret '.insightDetailVisible == true and all(.relevanceControls[]; .kind != "plugin" or .id != "org.example.notes" or (.muted == false and .followed == false))' || return 1
  press esc
  briefing_wait "Escape returns from project detail without closing Radar" '.insightDetailVisible == false and .opened == true' || return 1
  briefing_key setup 2 '.setupVisible == true and .setupCount >= 1 and .overviewContentY == 0' || return 1
  briefing_capture opening-04-my-setup || return 1
  briefing_key home 1 '.homeVisible == true' || return 1
  ssh_session "omarchy-theme-set catppuccin-latte >/dev/null" || return 1
  briefing_capture opening-05-light-home || return 1

  log "Empty Saved and filtered views have one recovery path and no inactive reader pane"
  briefing_key saved-empty 6 '.section == "saved" and .storyCount == 0 and .readerActionsEnabled == false and .inspectorVisible == false and .helperRunning == false' || return 1
  opening_empty_keys || return 1
  briefing_capture opening-06-empty-saved || return 1
  briefing_key plugin-search 4 '.section == "plugins" and .projecting == false' || return 1
  press slash
  type_text "radar-zero-results-91fef"
  briefing_wait "search reaches a genuinely empty local projection" '.storyCount == 0 and .helperRunning == false and .emptyRecoveryLabel == "Clear search"' || return 1
  press esc
  opening_empty_keys || return 1
  briefing_capture opening-07-empty-search || return 1
  press slash
  press ctrl-a
  press backspace
  press esc
  briefing_wait "clearing search restores source stories" '.storyCount > 0 and .projecting == false' || return 1

  log "The compositor's ordinary close chord preserves the remembered frame"
  press meta_l-w
  wait_for_guest_state "the window manager closes Radar" 15 ssh_session \
    "hyprctl -j clients | jq -e 'all(.[]; .title != \"📰 Omarchy News Radar\")'" || return 1
  briefing_open || return 1
  wait_for_guest_state "the window manager close also retains saved geometry" 15 ssh_session \
    "hyprctl -j clients | jq -e --argjson expected '$saved_geometry' '.[] | select(.title == \"📰 Omarchy News Radar\") | {at,size} == \$expected'" || return 1
  briefing_close || return 1

  if [[ -n ${RADAR_LAB_REAL_FEED:-} && -n ${RADAR_LAB_REAL_INSIGHTS:-} ]]; then
    log "Checking the same candidate with the real public edition and reviewed collections"
    test -f "$RADAR_LAB_REAL_FEED" && test -f "$RADAR_LAB_REAL_INSIGHTS" || return 1
    ssh_guest "cat >$scenario_root/fixtures/current.json" <"$RADAR_LAB_REAL_FEED" || return 1
    ssh_guest "cat >$scenario_root/candidate/tests/fixtures/insights-valid.json" <"$RADAR_LAB_REAL_INSIGHTS" || return 1
    ssh_guest "mv $scenario_root/xdg-state/omarchy-news-radar $scenario_root/state.synthetic && \
      mv $scenario_root/xdg-cache/omarchy-news-radar $scenario_root/cache.synthetic" || return 1
    ssh_session "omarchy-restart-shell" || return 1
    wait_for_guest_state "fresh session is available for real source content" 30 ssh_session "omarchy-shell shell ping" || return 1
    ssh_session "$plugin_dir/bin/news-radar-client refresh && $plugin_dir/bin/news-radar-client insights-refresh" >"$RUN_DIR/opening-real-cache.json" || return 1
    briefing_open || return 1
    wait_for_guest_state "the real edition reaches a stable first-use choice" 20 opening_choice_idle || return 1
    briefing_key real-browse ret '.homeVisible == true and .onboardingVisible == false and .insightsStatus == "cached" and .homeCards > 5' || return 1
    briefing_capture opening-08-real-home-light || return 1
    ssh_session "omarchy-theme-set matte-black >/dev/null" || return 1
    briefing_capture opening-09-real-home-dark || return 1
    for _card_step in {1..20}; do
      if ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.selectedHomeKind == \"collection\"'" >/dev/null; then break; fi
      press down
    done
    briefing_wait "keyboard reaches a reviewed real collection" '.selectedHomeKind == "collection"' || return 1
    selected_before="$(ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -r '.selectedHomeCard'")" || return 1
    geometry_before="$(ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar homeCardGeometry ''")" || return 1
    briefing_key real-card-right right ".selectedHomeCard == $((selected_before + 1)) and .selectedHomeKind == \"collection\"" || return 1
    geometry_after="$(ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar homeCardGeometry ''")" || return 1
    jq -e --argjson before "$geometry_before" \
      '.x > $before.x and ((.y + .height / 2) - ($before.y + $before.height / 2) | fabs) < 2' \
      <<<"$geometry_after" >/dev/null || return 1
    briefing_key real-card-left left ".selectedHomeCard == $selected_before and .selectedHomeKind == \"collection\"" || return 1
    briefing_key real-collection ret \
      '.insightDetailVisible == true and .insightSourceCount >= 2 and .insightReviewedAt != "" and .insightDetailReadingWidth > 0 and .insightDetailReadingWidth < .windowWidth and .insightDetailRelevanceColumns == 2' || return 1
    briefing_capture opening-09-real-collection || return 1
    collection_id="$(ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -r '.insightDetailId'")" || return 1
    project_id="$(jq -r --arg id "$collection_id" '.collections[] | select(.id == $id) | .projectIds[0]' "$RADAR_LAB_REAL_INSIGHTS")" || return 1
    project_name="$(jq -r --arg id "$project_id" '.projects[] | select(.id == $id) | .name' "$RADAR_LAB_REAL_INSIGHTS")" || return 1
    [[ $project_id =~ ^[a-zA-Z0-9._-]+$ && -n $project_name ]] || return 1
    briefing_key real-original-tab tab '.insightDetailFocusedControl == "Open original source"' || return 1
    while IFS= read -r source_label; do
      press tab
      source_focus="$(ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -r '.insightDetailFocusedControl'")" || return 1
      [[ $source_focus == "$source_label" ]] || { printf 'Unexpected source tab: %s (wanted %s)\n' "$source_focus" "$source_label"; return 1; }
    done < <(jq -r --arg id "$collection_id" '.collections[] | select(.id == $id) | . as $collection | .sourceLinks[] | select(.url != $collection.source.url) | .label' "$RADAR_LAB_REAL_INSIGHTS")
    briefing_key real-share-tab tab '.insightDetailFocusedControl == "Open share page"' || return 1
    briefing_resize 820 540 || return 1
    opening_focus_detail "$project_name" || return 1
    briefing_key real-project-detail ret \
      ".insightDetailId == \"$project_id\" and .insightDetailContentY == 0 and .insightDetailReadingWidth < .windowWidth and (.insightDetailHeroWidth == 0 or .insightDetailHeroWidth <= .insightDetailReadingWidth)" || return 1
    briefing_capture opening-09-real-project-notes || return 1
    briefing_key real-project-page pgdn \
      ".insightDetailId == \"$project_id\" and .insightDetailContentY >= 0 and .insightDetailFocusedControl == \"← Back to collection\"" || return 1
    briefing_key real-collection-return esc \
      ".insightDetailId == \"$collection_id\" and .insightDetailContentY == 0" || return 1
    briefing_resize 1120 720 || return 1
    press esc
    briefing_key real-setup 2 '.setupVisible == true and .overviewContentY == 0 and .projecting == false' || return 1
    briefing_capture opening-10-real-setup || return 1
    briefing_key real-home 1 '.homeVisible == true and .overviewContentY == 0' || return 1
  else
    briefing_open || return 1
  fi
  briefing_close || return 1
  log "A validated empty feed still has a complete, recoverable reader"
  ssh_guest "jq '.events = []' $scenario_root/fixtures/current.json >$scenario_root/fixtures/empty.json && \
    mv $scenario_root/fixtures/empty.json $scenario_root/fixtures/current.json && \
    mv $scenario_root/xdg-state/omarchy-news-radar $scenario_root/state.before-empty && \
    mv $scenario_root/xdg-cache/omarchy-news-radar $scenario_root/cache.before-empty" || return 1
  ssh_session "omarchy-restart-shell" || return 1
  wait_for_guest_state "session restarts for the isolated empty edition" 30 ssh_session "omarchy-shell shell ping" || return 1
  ssh_session "$plugin_dir/bin/news-radar-client refresh && $plugin_dir/bin/news-radar-client insights-refresh" >"$RUN_DIR/opening-empty-cache.json" || return 1
  briefing_open || return 1
  wait_for_guest_state "empty edition still offers first-use recovery" 20 opening_choice_idle || return 1
  briefing_key empty-browse ret '.homeVisible == true and .storyCount == 0 and .onboardingVisible == false and .inspectorVisible == false' || return 1
  briefing_capture opening-11-empty-feed-home || return 1
  briefing_key empty-core 3 '.section == "core" and .storyCount == 0 and .helperRunning == false' || return 1
  opening_empty_keys || return 1
  briefing_capture opening-12-empty-feed-source || return 1
  briefing_close || return 1
  opening_neighbors_unchanged || return 1
  while read -r neighbor_address; do
    [[ $neighbor_address =~ ^0x[0-9a-fA-F]{1,16}$ ]] || return 1
    ssh_session "hyprctl dispatch 'hl.dsp.window.close({ window = \"address:$neighbor_address\" })' >/dev/null" || return 1
  done < <(jq -r '.[].address' "$RUN_DIR/opening-neighbor-before.json")
  ssh_session "omarchy-plugin-remove io.github.mtolhuys.news-radar --yes" >"$RUN_DIR/opening-remove.log" || return 1
  ssh_session "cp $scenario_root/bindings.before \"\$HOME/.config/hypr/bindings.lua\" && hyprctl reload >/dev/null" || return 1
  ssh_guest "systemctl --user stop news-radar-briefing-fixture.service" || return 1
  ssh_session "journalctl --user --since '@$start_epoch' --no-pager" >"$RUN_DIR/opening-journal.log" || return 1
  if rg '(io.github.mtolhuys.news-radar|news-radar-briefing/candidate/src).*(ReferenceError|TypeError|Unable to assign|failed to load|Binding loop)|(ReferenceError|TypeError|Unable to assign|failed to load|Binding loop).*(io.github.mtolhuys.news-radar|news-radar-briefing/candidate/src)' "$RUN_DIR/opening-journal.log"; then return 1; fi
  printf 'ok - cached pre-map opening, stable neighboring geometry, preserved summon focus, saved placement, home, discovery, and setup\n'
}
