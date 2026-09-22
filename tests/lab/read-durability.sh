#!/bin/bash

# Focused reading-durability journey (D073): a dismissed Core story must stay
# read across ledger eviction and rematerialization. Every desktop and state
# mutation targets the disposable guest; the host only stages source.

omarchy_host_test() {
  local product_root plugin_dir helper start_epoch runtime_identity
  local news_id news_title test_env state_file
  local scenario_root=/tmp/news-radar-read-durability
  product_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
  runtime_identity="$(sed -n 's/.*property string runtimeBuildIdentity: "\([^"]*\)".*/\1/p' "$product_root/src/Panel.qml")"
  [[ $runtime_identity =~ ^news-radar-[0-9]+\.[0-9]+\.[0-9]+\+identity-2$ ]] || return 1
  start_epoch="$(date +%s)"
  # The disposable guest expands this path, never the host.
  # shellcheck disable=SC2016
  state_file='"${XDG_STATE_HOME:-$HOME/.local/state}"/omarchy-news-radar/state.json'

  # Older ShellCheck reports SC2317 for these harness callbacks.
  # shellcheck disable=SC2317,SC2329
  durability_state() {
    ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState ''" \
      | awk '/^\{.*\}$/ { value = $0 } END { print value }'
  }

  # shellcheck disable=SC2317,SC2329
  durability_wait() {
    local label="$1" predicate="$2"
    wait_for_guest_state "$label" 25 ssh_session \
      "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '$predicate'"
  }

  ssh_session "pkill -x hypridle >/dev/null 2>&1 || true; ! pgrep -x hypridle" || return 1

  log "Staging the exact candidate in the disposable guest"
  tar -C "$product_root" --exclude=.git --exclude=dist --exclude='__pycache__' -cf - . | ssh_guest \
    "rm -rf /tmp/omarchy-news-radar-candidate && mkdir -p /tmp/omarchy-news-radar-candidate && \
     tar -C /tmp/omarchy-news-radar-candidate -xf -"
  ssh_guest "git -C /tmp/omarchy-news-radar-candidate init -q && \
    git -C /tmp/omarchy-news-radar-candidate add . && \
    git -C /tmp/omarchy-news-radar-candidate -c user.name=PluginLab -c user.email=lab@invalid commit -qm candidate"
  ssh_guest "cd /tmp/omarchy-news-radar-candidate && make test && make validate" \
    >"$RUN_DIR/durability-source-tests.log" || return 1
  ssh_guest "rm -rf $scenario_root && mkdir -p $scenario_root/fixtures && \
    python3 /tmp/omarchy-news-radar-candidate/tests/lab/prepare_fixtures.py \
      /tmp/omarchy-news-radar-candidate/tests/fixtures/feed-valid.json $scenario_root/fixtures" || return 1

  log "Building the eviction and rematerialization editions"
  # present.json carries the Core story; evicted.json is the same edition after
  # ordinary marketplace volume pushed it out of the 500-event ledger;
  # returned.json is the next successful collect rematerializing the same
  # deterministic ID.
  ssh_guest "cd $scenario_root/fixtures && \
    jq '[.events[] | select(.classification.section == \"core\")][0]' valid.json >core-story.json && \
    jq --slurpfile s core-story.json '.generatedAt = \"2026-08-31T14:10:00Z\" |
        .window.through = \"2026-08-31T14:10:00Z\"' valid.json >present.json && \
    jq --slurpfile s core-story.json '.generatedAt = \"2026-08-31T14:20:00Z\" |
        .window.through = \"2026-08-31T14:20:00Z\" |
        .events = [.events[] | select(.id != \$s[0].id)]' valid.json >evicted.json && \
    jq --slurpfile s core-story.json '.generatedAt = \"2026-08-31T14:30:00Z\" |
        .window.through = \"2026-08-31T14:30:00Z\"' valid.json >returned.json && \
    cp present.json current.json" || return 1
  news_id="$(ssh_guest "jq -r '.id' $scenario_root/fixtures/core-story.json")" || return 1
  news_title="$(ssh_guest "jq -r '.title' $scenario_root/fixtures/core-story.json")" || return 1
  [[ $news_id =~ ^evt_[0-9a-f]{24}$ ]] || return 1
  ssh_guest "jq -e --arg id '$news_id' 'all(.events[]; .id != \$id)' $scenario_root/fixtures/evicted.json" >/dev/null || return 1
  ssh_guest "jq -e --arg id '$news_id' 'any(.events[]; .id == \$id)' $scenario_root/fixtures/returned.json" >/dev/null || return 1
  log "Core story under test: $news_title ($news_id)"

  log "Installing the candidate and its isolated loopback fixture"
  ssh_session "omarchy-plugin-add /tmp/omarchy-news-radar-candidate --enable --yes" \
    >"$RUN_DIR/durability-install.log" || return 1
  # shellcheck disable=SC2016
  plugin_dir='$HOME/.config/omarchy/plugins/io.github.mtolhuys.news-radar'
  helper="$plugin_dir/bin/news-radar-client"
  ssh_guest "systemd-run --user --unit=omarchy-news-radar-durability --collect --quiet -- \
      python3 /tmp/omarchy-news-radar-candidate/tests/lab/fixture_server.py --port 18767 --directory $scenario_root/fixtures"
  wait_for_guest_state "loopback fixture server is ready" 10 ssh_guest \
    "curl -fsS http://127.0.0.1:18767/current.json >/dev/null" || return 1
  test_env="OMARCHY_NEWS_RADAR_TEST_MODE=1 OMARCHY_NEWS_RADAR_TEST_FEED_URL=http://127.0.0.1:18767/current.json"
  ssh_session "mkdir -p \"\$HOME/.local/bin\" && \
    cp $plugin_dir/tests/lab/fixtures/xdg-open \"\$HOME/.local/bin/xdg-open\" && \
    chmod +x \"\$HOME/.local/bin/xdg-open\" && \
    printf '%s\n' \
      'hl.env(\"OMARCHY_NEWS_RADAR_TEST_MODE\", \"1\")' \
      'hl.env(\"OMARCHY_NEWS_RADAR_TEST_FEED_URL\", \"http://127.0.0.1:18767/current.json\")' \
      'hl.env(\"OMARCHY_NEWS_RADAR_TEST_TIMEOUT_SECONDS\", \"5\")' \
      'hl.env(\"PATH\", os.getenv(\"HOME\") .. \"/.local/bin:\" .. (os.getenv(\"PATH\") or \"/usr/bin\"))' \
      >>\"\$HOME/.config/hypr/bindings.lua\" && \
    hyprctl reload >/dev/null && test -z \"\$(hyprctl configerrors)\" && omarchy-restart-shell"
  wait_for_guest_state "restarted shell uses the exact candidate" 30 ssh_session \
    "omarchy-shell shell ping >/dev/null && \
     omarchy-plugin-list --json | jq -e 'any(.[]; .id == \"io.github.mtolhuys.news-radar\" and .enabled == true)'" || return 1
  ssh_session "$test_env $helper refresh" >"$RUN_DIR/durability-refresh.json" || return 1

  log "Dismissing the Core story through the rendered reader"
  ssh_session "omarchy-shell shell summon io.github.mtolhuys.news-radar" || return 1
  durability_wait "the panel presents its first-use choice" '.onboardingVisible == true' || return 1
  press ret
  durability_wait "Browse current stories opens Front Page" '.onboardingVisible == false' || return 1
  press 3
  durability_wait "the third section key reaches Core" \
    '.section == "core" and .projecting == false and .storyCount > 0' || return 1
  # Select the exact story under test, then make sure it is marked read.
  for _ in $(seq 1 14); do
    [[ "$(durability_state | jq -r '.selectedId')" == "$news_id" ]] && break
    press j
    sleep 0.3
  done
  durability_wait "the Core story under test is selected" ".selectedId == \"$news_id\"" || return 1
  if [[ "$(durability_state | jq -r '.selectedIsUnread')" == "true" ]]; then
    press u
  fi
  durability_wait "the reader shows the story as read" \
    ".selectedId == \"$news_id\" and .selectedIsUnread == false" || return 1
  ssh_session "jq -e --arg id '$news_id' '.readOverrides[\$id] == true' $state_file" || return 1
  capture_console "success-durability-01-dismissed"

  log "Evicting that story from the ledger, then reading something else"
  ssh_guest "cp $scenario_root/fixtures/evicted.json $scenario_root/fixtures/current.json" || return 1
  press r
  durability_wait "the evicted edition is adopted" '.refreshing == false' || return 1
  press 4
  durability_wait "the Plugins rail is ready for an ordinary read" \
    '.section == "plugins" and .projecting == false and .storyCount > 0' || return 1
  press j
  press u
  durability_wait "an unrelated story was read" '.projecting == false' || return 1
  ssh_session "jq -e --arg id '$news_id' '.readOverrides[\$id] == true' $state_file" || {
    ssh_session "cat $state_file" >"$RUN_DIR/durability-state-after-prune.json" 2>&1 || true
    printf 'the evicted story lost its dismissal after an unrelated read\n' >&2
    return 1
  }
  capture_console "success-durability-02-evicted"

  log "Rematerializing the identical deterministic ID"
  ssh_guest "cp $scenario_root/fixtures/returned.json $scenario_root/fixtures/current.json" || return 1
  press r
  durability_wait "the rematerialized edition is adopted" '.refreshing == false' || return 1
  press 3
  durability_wait "Core carries the returned story again" \
    '.section == "core" and .projecting == false and .storyCount > 0' || return 1
  ssh_session "$test_env $helper project --section core --installed-json '[]'" \
    >"$RUN_DIR/durability-core-projection.json" || return 1
  jq -e --arg id "$news_id" 'any(.events[]; .id == $id)' \
    "$RUN_DIR/durability-core-projection.json" >/dev/null || return 1
  jq -e --arg id "$news_id" 'any(.events[]; .id == $id and .isUnread == false)' \
    "$RUN_DIR/durability-core-projection.json" >/dev/null || {
      printf 'the rematerialized story resurfaced as unread\n' >&2
      return 1
    }
  ssh_session "jq -e --arg id '$news_id' '.readOverrides[\$id] == true and .schemaVersion == 13' $state_file" || return 1
  capture_console "success-durability-03-returned"

  log "Closing and removing the candidate"
  press esc
  wait_for_guest_state "the panel closes without an owned helper" 15 ssh_session \
    "hyprctl -j clients | jq -e 'all(.[]; .title != \"📰 Omarchy News Radar\")' && \
     ! pgrep -u \"\$USER\" -f '([/]bin/news-radar-client|[r]adar[.]cli_client)'" || return 1
  ssh_guest "systemctl --user stop omarchy-news-radar-durability >/dev/null 2>&1 || true"
  ssh_session "omarchy-plugin-remove io.github.mtolhuys.news-radar --yes" || return 1
  ssh_session "journalctl --user --since '@$start_epoch' --no-pager" >"$RUN_DIR/durability-journal.log" || true
  if grep -E 'io\.github\.mtolhuys\.news-radar.*(failed to load|ReferenceError|TypeError)|Panel\.qml.*(error|Error)' \
    "$RUN_DIR/durability-journal.log"; then
    return 1
  fi
  printf 'ok - a dismissed Core story survived ledger eviction, an unrelated read, and rematerialization under the same ID\n'
}
