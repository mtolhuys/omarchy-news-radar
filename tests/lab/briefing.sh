#!/bin/bash

# Focused briefing journey. All desktop and state mutations target the
# disposable guest; the host only stages source and retains evidence.

omarchy_host_test() {
  local product_root lab_root start_epoch runtime_identity
  local plugin_dir viewport_width viewport_height brief_id replacement_id saved_id
  local group_ids group_before group_after expected_source welcome_button_height section_index
  local section_ids=(front-page for-you core plugins youtube saved)
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

  # Require a short quiet interval: one completed helper can queue the next
  # projection, temporarily disabling visible controls between snapshots.
  # Older ShellCheck reports SC2317 for these harness callbacks/helpers.
  # shellcheck disable=SC2317,SC2329
  briefing_idle() {
    local attempt
    for ((attempt = 0; attempt < 5; attempt++)); do
      ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.windowVisible == true and .helperRunning == false and .briefingBusy == false and .pendingProjection == false'" >/dev/null || return 1
      sleep 0.25
    done
  }

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
    local frame monitors
    frame="$(ssh_session "hyprctl -j clients | jq '[.[] | select(.title == \"📰 Omarchy News Radar\")]'")" || return 1
    monitors="$(ssh_session "hyprctl -j monitors")" || return 1
    printf '%s\n' "$frame" >"$RUN_DIR/briefing-accessibility-frame.json"
    printf '%s\n' "$monitors" >"$RUN_DIR/briefing-accessibility-monitors.json"
    jq -e --argjson monitors "$monitors" '
      .[0] as $frame
      | (length == 1) as $unique
      | [$monitors[] | select(.id == $frame.monitor)][0] as $monitor
      | $unique and $monitor != null and $frame.at[0] >= ($monitor.x + $monitor.reserved[0])
        and $frame.at[1] >= ($monitor.y + $monitor.reserved[1])
        and ($frame.at[0] + $frame.size[0]) <= ($monitor.x + $monitor.width / $monitor.scale - $monitor.reserved[2])
        and ($frame.at[1] + $frame.size[1]) <= ($monitor.y + $monitor.height / $monitor.scale - $monitor.reserved[3])
    ' <<<"$frame" >/dev/null
  }

  briefing_control_fits() {
    local method="$1" geometry window
    geometry="$(ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar '$method' ''")" || return 1
    window="$(ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState ''")" || return 1
    printf '%s\n' "$geometry" >"$RUN_DIR/briefing-text-200-$method.json"
    jq -e --argjson window "$window" \
      '.visible == true and ((has("fullyVisible") | not) or .fullyVisible == true) and .width > 0 and .height > 0 and .x >= 0 and .y >= 0 and
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

  briefing_open() {
    local geometry bar_x bar_y
    geometry="$(ssh_session "omarchy-shell shell debugBarGeometry")" || return 1
    bar_x="$(jq -r '.[] | select(.id == "io.github.mtolhuys.news-radar" and .visible == true) | (.x + .width / 2) | floor' <<<"$geometry")"
    bar_y="$(jq -r '.[] | select(.id == "io.github.mtolhuys.news-radar" and .visible == true) | (.y + .height / 2) | floor' <<<"$geometry")"
    [[ $bar_x =~ ^[0-9]+$ && $bar_y =~ ^[0-9]+$ ]] || return 1
    radar_pointer_tap "$viewport_width" "$viewport_height" "$bar_x" "$bar_y" left || return 1
    if ! briefing_wait "newspaper opens the exact candidate window" \
      ".opened == true and .windowVisible == true and .build == \"$runtime_identity\" and .localStateReady == true"; then
      ssh_session "journalctl --user --since '@$start_epoch' --no-pager" >"$RUN_DIR/failed-opening-journal.log" || true
      ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState ''" >"$RUN_DIR/failed-opening-state.json" 2>&1 || true
      ssh_session "hyprctl -j clients" >"$RUN_DIR/failed-opening-clients.json" || true
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

  log "First use blocks implicit reading until a visible choice"
  briefing_open || return 1
  briefing_wait "welcome offers a stable finite briefing" \
    '.onboardingVisible == true and .briefing.initialized == true and .briefing.total > 0 and .briefing.total <= 5 and .briefingBusy == false and .refreshing == false' || return 1
  sleep 1
  ssh_session "jq -e '.onboardingComplete == false and (.readOverrides | length) == 0' $scenario_state" || return 1
  briefing_capture 01-welcome-dark || return 1
  wait_for_guest_state "first-use choices remain ready for input" 20 briefing_idle || return 1
  press ret
  briefing_wait "Browse keeps the backlog and dismisses the welcome choice" \
    '.onboardingVisible == false and .briefing.total <= 5 and .briefingBusy == false and .storyCount > 0' || return 1
  brief_id="$(ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -r '.briefing.id'")"
  [[ $brief_id =~ ^[0-9a-f]{64}$ ]] || return 1
  saved_id="$(ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -r '.selectedId'")"
  [[ $saved_id =~ ^evt_[0-9a-f]{24}$ ]] || return 1
  wait_for_guest_state "Home remains ready for the first story selection" 20 briefing_idle || return 1
  briefing_key enter-reader ret ' .homeVisible == false and .selectedIsUnread == false' || return 1
  press s
  wait_for_guest_state "Save persists the selected original story" 15 ssh_session \
    "jq -e '.saved | has(\"$saved_id\")' $scenario_state" || return 1
  briefing_capture 02-finite-briefing || return 1

  log "A plugin group reads only the occurrences explicitly listed in that group"
  press down
  press down
  briefing_wait "keyboard selects the installed Radar group" \
    '.selectedId == "evt_000000000000000000000b01" and .helperRunning == false' || return 1
  group_ids="$(ssh_guest "jq -c '.groupIds' $scenario_root/fixtures/expected.json")"
  group_before="$(ssh_guest "jq -c '.readOverrides' $scenario_state")"
  briefing_capture 03-group-before || return 1
  briefing_click groupReadGeometry || return 1
  briefing_wait "group reading settles without replacing the briefing" \
    ".briefing.id == \"$brief_id\" and .briefingBusy == false and .helperRunning == false" || return 1
  group_after="$(ssh_guest "jq -c '.readOverrides' $scenario_state")"
  jq -n -e --argjson before "$group_before" --argjson after "$group_after" --argjson members "$group_ids" \
    'all($members[]; . as $id | $after[$id] == true) and
     all(($before + $after | keys)[]; . as $id | if ($members | index($id)) == null then $before[$id] == $after[$id] else true end)' >/dev/null || return 1
  briefing_capture 04-group-read || return 1

  log "Keyboard focus reaches expanded source history in the narrow layout"
  briefing_resize 820 680 || return 1
  briefing_key 01-f6 f6 \
    '.section == "front-page" and .briefingControlsMode == true and .briefingFocusedControl == "Mark briefing read"' || return 1
  briefing_key 02-tab-new tab \
    '.section == "front-page" and .briefingControlsMode == true and .briefingFocusedControl == "New briefing"' || return 1
  briefing_key 03-backtab-finish shift-tab \
    '.section == "front-page" and .briefingControlsMode == true and .briefingFocusedControl == "Mark briefing read"' || return 1
  briefing_key 04-tab-new tab \
    '.section == "front-page" and .briefingControlsMode == true and .briefingFocusedControl == "New briefing"' || return 1
  briefing_key 05-tab-show tab \
    '.section == "front-page" and .briefingControlsMode == true and .briefingFocusedControl == "Show 3 updates"' || return 1
  briefing_key 06-expand ret \
    '.section == "front-page" and .groupExpanded == true and .briefingFocusedControl == "Hide 3 updates"' || return 1
  briefing_key 07-tab-history tab \
    '.section == "front-page" and .briefingControlsMode == true and .briefingFocusedControl == "Update history" and .groupHistoryIndex == 0' || return 1
  briefing_key 08-history-down down \
    '.section == "front-page" and .briefingFocusedControl == "Update history" and .groupHistoryIndex == 1' || return 1
  briefing_key 09-history-source ret \
    '.section == "front-page" and .selectedId == "evt_000000000000000000000b01"' || return 1
  expected_source="$(ssh_guest "jq -r '.events[] | select(.id == \"evt_000000000000000000000b02\") | .source.url' $scenario_root/fixtures/initial.json")"
  [[ $expected_source =~ ^https://github.com/example/radar-fixture/releases/tag/[0-9]+$ ]] || return 1
  wait_for_guest_state "Enter on the second history member opens its exact original source" 15 ssh_guest \
    "test \"\$(cat $scenario_root/xdg-state/omarchy-news-radar/lab-opened-url)\" = '$expected_source'" || return 1
  briefing_wait "history navigation leaves the representative selection intact" \
    '.selectedId == "evt_000000000000000000000b01" and .helperRunning == false' || return 1
  briefing_capture 04-expanded-narrow-dark || return 1
  ssh_session "omarchy-theme-set catppuccin-latte >/dev/null" || return 1
  briefing_capture 04-expanded-narrow-light || return 1
  press f6
  ssh_session "omarchy-theme-set matte-black >/dev/null" || return 1
  briefing_resize 1120 680 || return 1

  log "An explicitly completed briefing stays complete across refresh and reopen"
  briefing_click finishBriefingGeometry || return 1
  briefing_wait "the finite briefing is complete with more discoveries still available" \
    ".briefing.id == \"$brief_id\" and .briefing.complete == true and .briefing.remaining == 0 and .briefing.hasNewStories == true and .briefingBusy == false" || return 1
  briefing_capture 05-complete || return 1
  press r
  briefing_wait "refresh preserves completion and exact membership" \
    ".briefing.id == \"$brief_id\" and .briefing.complete == true and .refreshing == false" || return 1
  briefing_close || return 1
  briefing_open || return 1
  briefing_wait "reopening retains the complete briefing" \
    ".briefing.id == \"$brief_id\" and .briefing.complete == true and .onboardingVisible == false" || return 1
  wait_for_guest_state "New briefing remains ready for input" 20 briefing_idle || return 1
  briefing_click newBriefingGeometry || return 1
  briefing_wait "New briefing explicitly selects another eligible discovery" \
    ".briefing.id != \"$brief_id\" and .briefing.total > 0 and .briefing.total <= 5 and .briefing.remaining > 0 and .briefingBusy == false" || return 1
  replacement_id="$(ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -r '.briefing.id'")"
  ssh_session "jq -e '.saved | has(\"$saved_id\")' $scenario_state" || return 1
  briefing_capture 06-next-briefing || return 1

  log "Reviewing the same briefing in maintained light and narrow layouts"
  ssh_session "omarchy-theme-set catppuccin-latte >/dev/null" || return 1
  briefing_wait "light-theme reprojection preserves membership" \
    ".briefing.id == \"$replacement_id\" and .windowVisible == true and .helperRunning == false" || return 1
  briefing_capture 07-light || return 1
  briefing_resize 820 680 || return 1
  briefing_wait "narrow layout retains a usable finite briefing" \
    ".briefing.id == \"$replacement_id\" and .windowWidth <= 850 and .windowHeight > 0 and .storyCount > 0" || return 1
  briefing_capture 08-narrow-light || return 1
  ssh_session "omarchy-theme-set matte-black >/dev/null" || return 1
  briefing_capture 09-narrow-dark || return 1
  briefing_close || return 1

  log "Starting from today clears exact displayed backlog and preserves saved stories"
  # Only the disposable fixture state is reset. Preserve the bookmark created
  # through the real control to prove onboarding never clears saved records.
  ssh_guest "jq '.onboardingComplete = false | .briefing = null | .readOverrides = {} | .readThrough = \"1970-01-01T00:00:00Z\"' \
    $scenario_state >$scenario_root/fresh-state.json && chmod 600 $scenario_root/fresh-state.json && \
    mv $scenario_root/fresh-state.json $scenario_state" || return 1
  briefing_open || return 1
  briefing_wait "fresh private fixture state exposes Start from today" \
    '.onboardingVisible == true and .briefingBusy == false and .refreshing == false' || return 1
  log "The welcome choices remain visible at 200 percent text size"
  welcome_button_height="$(ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar browseStoriesGeometry '' | jq -r '.height'")"
  [[ $welcome_button_height =~ ^[0-9]+([.][0-9]+)?$ ]] || return 1
  ssh_guest "if test -f \"\$HOME/.config/omarchy/shell.toml\"; then \
      cp -p \"\$HOME/.config/omarchy/shell.toml\" $scenario_root/shell.toml.before; \
    else touch $scenario_root/shell.toml.was-missing; fi && \
    printf '[font]\nbase-size = 24\n' >\"\$HOME/.config/omarchy/shell.toml\"" || return 1
  wait_for_guest_state "live Style increases the rendered welcome button height" 20 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar browseStoriesGeometry '' | jq -e '.height > $welcome_button_height'" || return 1
  wait_for_guest_state "live enlarged text automatically fits the existing window" 20 briefing_frame_fits || return 1
  wait_for_guest_state "both scaled welcome choices fit inside the actual window" 20 briefing_choices_fit welcome-200 || return 1
  briefing_capture 10-welcome-text-200 || return 1
  briefing_close || return 1
  briefing_open || return 1
  wait_for_guest_state "opening with enlarged text fits the workarea" 20 briefing_frame_fits || return 1
  wait_for_guest_state "fresh opening retains both enlarged first-use choices" 20 briefing_choices_fit welcome-reopened-200 || return 1
  briefing_capture 10-welcome-reopened-text-200 || return 1
  wait_for_guest_state "Start today remains ready for input" 20 briefing_idle || return 1
  briefing_click startTodayGeometry || return 1
  briefing_wait "Start from today at 200 percent leaves an empty completed briefing" \
    '.onboardingVisible == false and .briefing.complete == true and .briefing.total == 0 and .briefingBusy == false' || return 1
  ssh_guest "jq -e --slurpfile expected $scenario_root/fixtures/expected.json \
    '. as \$state | .onboardingComplete == true and .readThrough == \"1970-01-01T00:00:00Z\" and \
     all(\$expected[0].initialIds[]; . as \$id | \$state.readOverrides[\$id] == true) and \
     (.saved | has(\"$saved_id\"))' $scenario_state" || return 1
  briefing_key text-200-home-page pgdn '.homeVisible == true and .overviewContentY > 0' || return 1
  wait_for_guest_state "normal Front Page keeps New briefing in the 200 percent window" 15 briefing_control_fits newBriefingGeometry || return 1
  briefing_wait "the expanded text produces a scrollable section rail" \
    '.sectionRail.contentHeight > .sectionRail.viewport.height and .sectionRail.viewport.height > 0' || return 1
  for section_index in "${!section_ids[@]}"; do
    briefing_key "text-200-section-$section_index" "$((section_index + 1))" \
      ".section == \"${section_ids[$section_index]}\" and .projecting == false and
       .sectionRail.selectedFullyVisible == true and .sectionRail.viewport.x >= 0 and .sectionRail.viewport.y >= 0 and
       (.sectionRail.viewport.x + .sectionRail.viewport.width) <= (.windowWidth + 1) and
       (.sectionRail.viewport.y + .sectionRail.viewport.height) <= (.windowHeight + 1)" || return 1
  done
  briefing_capture 10-text-200-saved-section || return 1
  briefing_key text-200-return-front 1 \
    '.section == "front-page" and .sectionRail.selectedFullyVisible == true and .projecting == false' || return 1
  briefing_key text-200-return-page pgdn ' .homeVisible == true and .overviewContentY > 0' || return 1
  briefing_control_fits newBriefingGeometry || return 1
  briefing_capture 10-started-today-text-200 || return 1

  # New briefing is disabled when all displayed events are read. Expose the
  # later fixture while text is still enlarged, then activate the real control.
  ssh_guest "cp $scenario_root/fixtures/later.json $scenario_root/fixtures/current.json" || return 1
  press r
  briefing_wait "a newly discovered older occurrence stays outside the completed briefing" \
    '.briefing.complete == true and .briefing.total == 0 and .briefing.hasNewStories == true and .refreshing == false and .briefingBusy == false' || return 1
  ssh_guest "jq -e '.readThrough == \"1970-01-01T00:00:00Z\" and (.readOverrides | has(\"evt_000000000000000000001a7e\") | not)' $scenario_state" || return 1
  briefing_key text-200-new-brief-focus f6 \
    '.section == "front-page" and .briefingControlsMode == true and .briefingFocusedControl == "New briefing"' || return 1
  briefing_control_fits newBriefingGeometry || return 1
  briefing_key text-200-new-brief-activate ret \
    '.briefing.total == 1 and .briefing.remaining == 1 and .selectedId == "evt_000000000000000000001a7e" and .selectedIsUnread == true and .briefingBusy == false' || return 1
  ssh_guest "jq -e '.saved | has(\"$saved_id\")' $scenario_state" || return 1
  briefing_key text-200-late-card down \
    '.homeVisible == true and .selectedHomeKind == "story" and .selectedIsUnread == true' || return 1
  ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar homeCardGeometry ''" \
    >"$RUN_DIR/briefing-text-200-home-card.json" || return 1
  briefing_control_fits homeCardGeometry || return 1
  briefing_capture 11-older-arrival-unread-text-200 || return 1

  ssh_guest "if test -f $scenario_root/shell.toml.was-missing; then \
      rm \"\$HOME/.config/omarchy/shell.toml\"; \
    else cp -p $scenario_root/shell.toml.before \"\$HOME/.config/omarchy/shell.toml\"; fi" || return 1
  wait_for_guest_state "restoring the guest font restores the welcome button size" 20 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar browseStoriesGeometry '' | jq -e '.height == $welcome_button_height'" || return 1
  briefing_wait "restored text retains the same unread late-arrival briefing" \
    '.briefing.total == 1 and .briefing.remaining == 1 and .selectedId == "evt_000000000000000000001a7e" and .selectedIsUnread == true' || return 1
  briefing_capture 11-older-arrival-unread || return 1

  log "Checking personal news, stable unread badges, and visible filter controls"
  # A legacy broad follow must not duplicate marketplace news in For You.
  ssh_guest "jq '.relevance.followedSources = [\"marketplace\"]' $scenario_state > $scenario_root/state.next && mv $scenario_root/state.next $scenario_state" || return 1
  briefing_key personal-news-direct 2 \
    '.section == "for-you" and .setupVisible == false and .projecting == false and .totalStories == 3 and .sectionRail.badges["for-you"] == 0' || return 1
  briefing_key personal-setup-focus f6 '.briefingFocusedControl == "My setup"' || return 1
  briefing_key personal-setup-open ret '.setupVisible == true' || return 1
  briefing_key personal-setup-footer end '.homeFooterSelected == true' || return 1
  briefing_key personal-setup-news ret '.setupVisible == false and .totalStories == 3' || return 1
  briefing_key plugins-all 4 \
    '.section == "plugins" and .projecting == false and .totalStories == 7 and .unreadCount == 1 and .sectionRail.badges.plugins == 1' || return 1
  briefing_key plugins-unread f \
    '.projecting == false and .totalStories == 1 and .hiddenReadStories == 6 and .unreadCount == 1 and .sectionRail.badges.plugins == 1' || return 1
  briefing_capture 12-plugins-unread || return 1
  briefing_key plugins-all-again f \
    '.projecting == false and .totalStories == 7 and .hiddenReadStories == 0 and .sectionRail.badges.plugins == 1' || return 1
  briefing_resize 1080 760 || return 1
  briefing_control_fits settingsGeometry || return 1
  briefing_capture 13-plugin-controls || return 1
  briefing_click settingsGeometry || return 1
  briefing_wait "Settings is clickable in the resized reader" '.sectionSettingsOpen == true' || return 1
  briefing_key settings-close esc '.sectionSettingsOpen == false' || return 1

  log "Removing the isolated candidate and checking runtime cleanup"
  briefing_close || return 1
  ssh_session "omarchy-plugin-remove io.github.mtolhuys.news-radar --yes" >"$RUN_DIR/briefing-remove.log" || return 1
  wait_for_guest_state "removal unloads the plugin and retains private reading state" 15 ssh_session \
    "test ! -e $plugin_dir && test -f $scenario_state && \
     omarchy-plugin-list --json | jq -e 'all(.[]; .id != \"io.github.mtolhuys.news-radar\")'" || return 1
  ssh_guest "systemctl --user stop news-radar-briefing-fixture.service" || return 1
  ssh_session "cp $scenario_root/bindings.before \"\$HOME/.config/hypr/bindings.lua\" && \
    hyprctl reload >/dev/null && test -z \"\$(hyprctl configerrors)\"" || return 1
  ssh_session "journalctl --user --since '@$start_epoch' --no-pager" >"$RUN_DIR/briefing-journal.log" || return 1
  if grep -E 'io\.github\.mtolhuys\.news-radar.*(failed to load|ReferenceError|TypeError)|(Panel|BarWidget|BriefingGroup|BriefingNotice|WelcomeCard)\.qml.*(error|Error)' \
    "$RUN_DIR/briefing-journal.log"; then
    return 1
  fi
  printf 'ok - finite briefing, explicit group reading, durable completion, new briefing, first-use choices, saved state, late arrivals, theme/layout, and removal assertions passed\n'
}
