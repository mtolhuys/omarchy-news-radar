#!/bin/bash

# Focused notify-only update journey (D074): when the plugin's origin publishes
# a newer release, Radar must show a notice and must never install it. Every
# desktop and state mutation targets the disposable guest.

omarchy_host_test() {
  local product_root plugin_dir start_epoch runtime_identity
  local installed_before installed_version newer_commit git_before git_after
  local candidate=/tmp/omarchy-news-radar-candidate
  local scenario_root=/tmp/news-radar-update-notice
  product_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
  runtime_identity="$(sed -n 's/.*property string runtimeBuildIdentity: "\([^"]*\)".*/\1/p' "$product_root/src/Panel.qml")"
  [[ $runtime_identity =~ ^news-radar-[0-9]+\.[0-9]+\.[0-9]+\+identity-2$ ]] || return 1
  start_epoch="$(date +%s)"
  # The disposable guest expands this path, never the host.
  # shellcheck disable=SC2016
  plugin_dir='$HOME/.config/omarchy/plugins/io.github.mtolhuys.news-radar'

  # Older ShellCheck reports SC2317 for these harness callbacks.
  # shellcheck disable=SC2317,SC2329
  notice_wait() {
    local label="$1" predicate="$2"
    wait_for_guest_state "$label" 30 ssh_session \
      "omarchy-shell shell call io.github.mtolhuys.news-radar debugState '' | jq -e '$predicate'"
  }

  ssh_session "pkill -x hypridle >/dev/null 2>&1 || true; ! pgrep -x hypridle" || return 1

  log "Staging the exact candidate as the plugin's local origin"
  tar -C "$product_root" --exclude=.git --exclude=dist --exclude='__pycache__' -cf - . | ssh_guest \
    "rm -rf $candidate && mkdir -p $candidate && tar -C $candidate -xf -"
  ssh_guest "git -C $candidate init -q -b main && git -C $candidate add . && \
    git -C $candidate -c user.name=PluginLab -c user.email=lab@invalid commit -qm candidate"
  ssh_guest "cd $candidate && make test && make validate" >"$RUN_DIR/update-notice-source-tests.log" || return 1
  ssh_guest "rm -rf $scenario_root && mkdir -p $scenario_root/fixtures && \
    python3 $candidate/tests/lab/prepare_fixtures.py $candidate/tests/fixtures/feed-valid.json $scenario_root/fixtures && \
    cp $scenario_root/fixtures/valid.json $scenario_root/fixtures/current.json" || return 1

  log "Installing the candidate from that origin"
  ssh_session "omarchy-plugin-add $candidate --enable --yes" >"$RUN_DIR/update-notice-install.log" || return 1
  installed_before="$(ssh_session "git -C $plugin_dir rev-parse HEAD")" || return 1
  installed_version="$(ssh_session "jq -r .version $plugin_dir/manifest.json")" || return 1
  [[ $installed_before =~ ^[0-9a-f]{40}$ && $installed_version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || return 1
  log "Installed $installed_version at $installed_before"

  ssh_guest "systemd-run --user --unit=omarchy-news-radar-update-notice --collect --quiet -- \
      python3 $candidate/tests/lab/fixture_server.py --port 18768 --directory $scenario_root/fixtures"
  wait_for_guest_state "loopback fixture server is ready" 10 ssh_guest \
    "curl -fsS http://127.0.0.1:18768/current.json >/dev/null" || return 1
  ssh_session "printf '%s\n' \
      'hl.env(\"OMARCHY_NEWS_RADAR_TEST_MODE\", \"1\")' \
      'hl.env(\"OMARCHY_NEWS_RADAR_TEST_FEED_URL\", \"http://127.0.0.1:18768/current.json\")' \
      'hl.env(\"OMARCHY_NEWS_RADAR_TEST_TIMEOUT_SECONDS\", \"5\")' \
      >>\"\$HOME/.config/hypr/bindings.lua\" && \
    hyprctl reload >/dev/null && test -z \"\$(hyprctl configerrors)\" && omarchy-restart-shell"
  wait_for_guest_state "restarted shell uses the exact candidate" 30 ssh_session \
    "omarchy-shell shell ping >/dev/null && \
     omarchy-plugin-list --json | jq -e 'any(.[]; .id == \"io.github.mtolhuys.news-radar\" and .enabled == true)'" || return 1

  log "The origin's mutable default branch now names a newer release"
  ssh_guest "cd $candidate && jq '.version = \"99.0.0\"' manifest.json >manifest.next && mv manifest.next manifest.json && \
    git -c user.name=PluginLab -c user.email=lab@invalid commit -qam 'unverified newer release'" || return 1
  newer_commit="$(ssh_guest "git -C $candidate rev-parse HEAD")" || return 1
  [[ $newer_commit != "$installed_before" ]] || return 1

  # Fingerprint the installed plugin's own repository: the check must fetch
  # into a throwaway repository and write nothing here, not even FETCH_HEAD.
  # shellcheck disable=SC2016
  git_before="$(ssh_session "cd $plugin_dir/.git && { if test -e FETCH_HEAD; then sha256sum FETCH_HEAD; else echo no-FETCH_HEAD; fi; \
    git count-objects -v | grep -E '^(count|in-pack|packs):'; find refs -type f | sort | xargs -r sha256sum; }")" || return 1

  log "Opening Radar: it must report the release and install nothing"
  ssh_session "omarchy-shell shell summon io.github.mtolhuys.news-radar" || return 1
  notice_wait "the panel reports the newer release as a notice" \
    '.pluginUpdateState == "behind" and .pluginUpdateNoticeVisible == true and
     .pluginUpdateCheckRunning == false and (.pluginUpdateMessage | test("99\\.0\\.0")) and
     (.pluginUpdateMessage | test("marketplace"))' || {
      ssh_session "omarchy-shell shell call io.github.mtolhuys.news-radar debugState ''" \
        >"$RUN_DIR/update-notice-failure-state.json" 2>&1 || true
      capture_console "failure-update-notice"
      return 1
    }
  capture_console "success-update-notice-01-notice"

  # Give any install path every chance to run before proving none did.
  sleep 5
  ssh_session "test \"\$(git -C $plugin_dir rev-parse HEAD)\" = '$installed_before' && \
    test \"\$(jq -r .version $plugin_dir/manifest.json)\" = '$installed_version' && \
    test -z \"\$(git -C $plugin_dir status --porcelain)\"" || {
      printf 'the installed checkout moved after an update notice\n' >&2
      return 1
    }
  git_after="$(ssh_session "cd $plugin_dir/.git && { if test -e FETCH_HEAD; then sha256sum FETCH_HEAD; else echo no-FETCH_HEAD; fi; \
    git count-objects -v | grep -E '^(count|in-pack|packs):'; find refs -type f | sort | xargs -r sha256sum; }")" || return 1
  printf '%s\n' "$git_before" >"$RUN_DIR/update-notice-plugin-git-before.txt"
  printf '%s\n' "$git_after" >"$RUN_DIR/update-notice-plugin-git-after.txt"
  [[ $git_before == "$git_after" ]] || {
    printf 'the update check wrote inside the installed plugin repository\n' >&2
    return 1
  }
  # The helper itself must refuse the removed install command.
  ssh_session "! $plugin_dir/bin/news-radar-client update-apply >/dev/null 2>&1" || return 1
  ssh_session "$plugin_dir/bin/news-radar-client update-status" >"$RUN_DIR/update-notice-status.json" || return 1
  jq -e --arg newer "$newer_commit" \
    '.state == "behind" and .updateAvailable == true and .canApply == false and
     .availableCommit == $newer and .availableVersion == "99.0.0" and (has("updater") | not)' \
    "$RUN_DIR/update-notice-status.json" >/dev/null || return 1
  capture_console "success-update-notice-02-unchanged"

  log "Closing and removing the candidate"
  press esc
  wait_for_guest_state "the panel closes without an owned helper" 15 ssh_session \
    "hyprctl -j clients | jq -e 'all(.[]; .title != \"📰 Omarchy News Radar\")' && \
     ! pgrep -u \"\$USER\" -f '([/]bin/news-radar-client|[r]adar[.]cli_client)'" || return 1
  ssh_guest "systemctl --user stop omarchy-news-radar-update-notice >/dev/null 2>&1 || true"
  ssh_session "omarchy-plugin-remove io.github.mtolhuys.news-radar --yes" || return 1
  ssh_session "journalctl --user --since '@$start_epoch' --no-pager" >"$RUN_DIR/update-notice-journal.log" || true
  if grep -E 'omarchy-plugin-update .*news-radar|io\.github\.mtolhuys\.news-radar.*(failed to load|ReferenceError|TypeError)|Panel\.qml.*(error|Error)' \
    "$RUN_DIR/update-notice-journal.log"; then
    return 1
  fi
  printf 'ok - a newer origin release produced a marketplace notice, nothing inside the installed plugin changed, and no install path remained\n'
}
