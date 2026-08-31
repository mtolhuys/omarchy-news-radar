#!/bin/bash

# Full product-owned journey. The harness runs this function only inside a
# disposable Omarchy guest; the daily host is used solely to stage source and
# retain evidence.

omarchy_host_test() {
  local product_root lab_root start_epoch before_hash after_hash before_change_count
  local helper shortcut plugin_dir viewport_width viewport_height monitor_name bar_x bar_y tune_x tune_y
  local open_started_ms open_ready_ms dense_started_ms dense_ready_ms close_started_ms close_ready_ms
  local shell_rss_open shell_rss_closed projection_seconds
  product_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
  lab_root="$(cd -- "$product_root/../../omarchy/plugin-lab" && pwd)"
  # shellcheck source=/dev/null
  source "$lab_root/host-tests/helpers/pointer.sh"
  start_epoch="$(date +%s)"

  log "Staging the exact News Radar candidate in the disposable guest"
  tar -C "$product_root" --exclude=.git --exclude=dist --exclude='__pycache__' -cf - . | ssh_guest \
    "rm -rf /tmp/omarchy-news-radar-candidate && mkdir -p /tmp/omarchy-news-radar-candidate && tar -C /tmp/omarchy-news-radar-candidate -xf -"
  ssh_guest "git -C /tmp/omarchy-news-radar-candidate init -q && \
    git -C /tmp/omarchy-news-radar-candidate add . && \
    git -C /tmp/omarchy-news-radar-candidate -c user.name=PluginLab -c user.email=lab@invalid commit -qm candidate"
  ssh_guest "cd /tmp/omarchy-news-radar-candidate && make test && make validate" \
    >"$RUN_DIR/news-radar-source-tests.log" || return 1
  ssh_guest "python3 /tmp/omarchy-news-radar-candidate/tests/lab/prepare_fixtures.py \
    /tmp/omarchy-news-radar-candidate/tests/fixtures/feed-valid.json /tmp/news-radar-fixtures" || return 1

  log "Installing the candidate and a synthetic locally installed plugin"
  ssh_session "omarchy-plugin-add /tmp/omarchy-news-radar-candidate --enable --yes" \
    >"$RUN_DIR/news-radar-install.log" || return 1
  ssh_guest "rm -rf /tmp/news-radar-installed-plugin && mkdir -p /tmp/news-radar-installed-plugin && \
    printf '%s\n' '{\"schemaVersion\":1,\"id\":\"io.github.mtolhuys.disk-lens\",\"name\":\"Disk Lens fixture\",\"version\":\"1.0.0\",\"kinds\":[\"service\"],\"entryPoints\":{\"service\":\"Service.qml\"}}' >/tmp/news-radar-installed-plugin/manifest.json && \
    printf '%s\n' 'import QtQuick' 'Item {}' >/tmp/news-radar-installed-plugin/Service.qml && \
    git -C /tmp/news-radar-installed-plugin init -q && git -C /tmp/news-radar-installed-plugin add . && \
    git -C /tmp/news-radar-installed-plugin -c user.name=PluginLab -c user.email=lab@invalid commit -qm fixture"
  ssh_session "omarchy-plugin-add /tmp/news-radar-installed-plugin --enable --yes" >/dev/null || return 1

  wait_for_guest_state "candidate and relevance fixture are installed and enabled" 20 ssh_session \
    "omarchy-plugin-list --json | jq -e 'any(.[]; .id == \"io.github.mtolhuys.news-radar\" and .enabled == true) and any(.[]; .id == \"io.github.mtolhuys.disk-lens\" and .enabled == true)'" || return 1
  ssh_session "omarchy-shell shell listPlugins" >"$RUN_DIR/news-radar-plugin-list.json" || return 1
  jq -e 'any(.[]; .id == "io.github.mtolhuys.news-radar" and .kinds == ["panel", "bar-widget"] and .enabled == true)' \
    "$RUN_DIR/news-radar-plugin-list.json" >/dev/null || return 1

  # The literal is expanded by the disposable guest's shell, not the host.
  # shellcheck disable=SC2016
  plugin_dir='$HOME/.config/omarchy/plugins/io.github.mtolhuys.news-radar'
  helper="$plugin_dir/bin/news-radar-client"
  shortcut="$plugin_dir/bin/news-radar-shortcut"

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
      >>\"\$HOME/.config/hypr/bindings.lua\" && \
    hyprctl reload >/dev/null && test -z \"\$(hyprctl configerrors)\" && omarchy-restart-shell"
  wait_for_guest_state "restarted shell uses the exact candidate" 30 ssh_session \
    "omarchy-shell shell ping >/dev/null && omarchy-plugin-list --json | jq -e 'any(.[]; .id == \"io.github.mtolhuys.news-radar\" and .enabled == true)'" || return 1

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
    "hyprctl -j layers | jq -e '[.. | objects | select(.namespace? == \"omarchy-news-radar\")] | length >= 1'" || return 1
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
  tune_x="$(ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar tuneNewspaperGeometry '' | jq -r 'select(.visible == true) | (.x + (.width / 2) | floor)'")" || return 1
  tune_y="$(ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar tuneNewspaperGeometry '' | jq -r 'select(.visible == true) | (.y + (.height / 2) | floor)'")" || return 1
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
    "hyprctl -j layers | jq -e '[.. | objects | select(.namespace? == \"omarchy-news-radar\")] | length >= 1'" || return 1
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
    "hyprctl -j layers | jq -e '[.. | objects | select(.namespace? == \"omarchy-news-radar\")] | length == 0' && ! pgrep -u \"\$USER\" -f '[/]bin/news-radar-client'" || return 1

  log "Proving cached-first reading, offline preservation, and pointer close"
  ssh_guest "cp /tmp/news-radar-fixtures/valid.json /tmp/news-radar-fixtures/current.json"
  ssh_session "OMARCHY_NEWS_RADAR_TEST_MODE=1 OMARCHY_NEWS_RADAR_TEST_FEED_URL=http://127.0.0.1:18765/current.json $helper refresh" \
    >"$RUN_DIR/news-radar-seed-cache.json" || return 1
  ssh_guest "rm -f /tmp/news-radar-fixtures/current.json"
  press meta_l-alt-n
  wait_for_guest_state "cached fixture remains visible after offline refresh" 20 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.opened == true and .status == \"Offline\" and .storyCount > 0 and (.selectedTitle | length > 0)'" || return 1
  capture_console "success-news-radar-02-cached-offline"
  qmp_pointer_tap "$viewport_width" "$viewport_height" $((viewport_width / 2 + 500)) $((viewport_height / 2 - 330)) left
  if ! wait_for_guest_state "visible close control responds to QMP pointer input" 8 ssh_session \
    "hyprctl -j layers | jq -e '[.. | objects | select(.namespace? == \"omarchy-news-radar\")] | length == 0'"; then
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
  press ctrl_l-a
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
  press 1
  wait_for_guest_state "empty valid edition has a visible empty state" 15 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.status == \"Current\" and .storyCount == 0'" || return 1
  capture_console "success-news-radar-07-empty"
  ssh_guest "cp /tmp/news-radar-fixtures/dense.json /tmp/news-radar-fixtures/current.json"
  press r
  press 4
  wait_for_guest_state "dense 120-story projection remains navigable" 15 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.status == \"Current\" and .storyCount == 120'" || return 1
  shell_rss_open="$(ssh_session "ps -o rss= -p \"\$(pgrep -n -u \"\$USER\" quickshell)\" | tr -d ' '")"
  projection_seconds="$(ssh_session "TIMEFORMAT='%R'; { time $helper project --section plugins --installed-json '[]' --query '' >/dev/null; } 2>/tmp/news-radar-projection.time && cat /tmp/news-radar-projection.time")" || return 1
  dense_started_ms="$(date +%s%3N)"
  press end
  wait_for_guest_state "End reaches the bounded dense model tail" 10 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.selectedIndex == 119'" || return 1
  dense_ready_ms="$(date +%s%3N)"
  capture_console "success-news-radar-08-dense"
  ssh_guest "cp /tmp/news-radar-fixtures/long.json /tmp/news-radar-fixtures/current.json"
  press r
  press 2
  wait_for_guest_state "long Unicode story renders as plain text" 15 ssh_session \
    "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '.storyCount > 0 and (.selectedTitle | startswith(\"長い見出し\"))'" || return 1

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
    "hyprctl -j layers | jq -e '[.. | objects | select(.namespace? == \"omarchy-news-radar\")] | length == 0' && ! pgrep -u \"\$USER\" -f '[/]bin/news-radar-client'" || return 1
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
    '{context:"disposable Plugin Lab VM; shared shell RSS is observational, not plugin-exclusive", openLatencyMs:$openLatencyMs, projection120Seconds:($projectionSeconds|tonumber), denseEndLatencyMs:$denseEndLatencyMs, closeTeardownMs:$closeTeardownMs, helperProcessesAfterClose:0, shellRssOpenKiB:$shellRssOpenKiB, shellRssClosedKiB:$shellRssClosedKiB}' \
    >"$RUN_DIR/news-radar-performance.json" || return 1

  log "Proving same-path runtime replacement and clean lifecycle removal"
  before_change_count="$(ssh_session "journalctl --user -t omarchy-shell --since '@$start_epoch' --no-pager | grep -Fc 'Local plugin changed, reloading: io.github.mtolhuys.news-radar' || true")"
  ssh_session "sed -i 's/news-radar-0.1.0+panel-4/news-radar-0.1.0+panel-5/' $plugin_dir/src/Panel.qml"
  wait_for_guest_state "shell observes the same-path candidate update" 20 ssh_session \
    "test \"\$(journalctl --user -t omarchy-shell --since '@$start_epoch' --no-pager | grep -Fc 'Local plugin changed, reloading: io.github.mtolhuys.news-radar' || true)\" -gt '$before_change_count'" || return 1
  ssh_session "omarchy-shell shell toggle io.github.mtolhuys.news-radar '{}'"
  wait_for_guest_state "same-path panel update replaces the live runtime identity" 20 ssh_session \
    "test \"\$(omarchy-shell shell call io.github.mtolhuys.news-radar runtimeIdentity '')\" = news-radar-0.1.0+panel-5" || return 1
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
  ssh_session "omarchy-plugin-remove io.github.mtolhuys.news-radar --yes"
  wait_for_guest_state "plugin removal unloads files and preserves user state" 15 ssh_session \
    "test ! -e \"\$HOME/.config/omarchy/plugins/io.github.mtolhuys.news-radar\" && test -f \"\${XDG_STATE_HOME:-\$HOME/.local/state}/omarchy-news-radar/state.json\" && omarchy-plugin-list --json | jq -e 'all(.[]; .id != \"io.github.mtolhuys.news-radar\")'" || return 1
  ssh_session "omarchy-plugin-remove io.github.mtolhuys.disk-lens --yes" >/dev/null || return 1
  ssh_session "journalctl --user --since '@$start_epoch' --no-pager" >"$RUN_DIR/news-radar-user-journal.log" || true
  if grep -E 'io\.github\.mtolhuys\.news-radar.*(failed to load|ReferenceError|TypeError)|(Panel|BarWidget)\.qml.*(error|Error)' \
    "$RUN_DIR/news-radar-user-journal.log"; then
    echo "News Radar runtime errors were present in the guest journal" >&2
    return 1
  fi
  ssh_session "test -z \"\$(hyprctl configerrors)\" && ! pgrep -u \"\$USER\" -f '[/]bin/news-radar-client'" || return 1
  ssh_guest "systemctl --user stop omarchy-news-radar-fixture.service 2>/dev/null || true"
  capture_console "success-news-radar-14-shortcut-removed-editor-intact"

  printf 'ok - exact candidate passed newspaper, images, interests, shortcut, cached-first, keyboard, pointer, source, state, failure, visual, update, and lifecycle assertions\n'
}
