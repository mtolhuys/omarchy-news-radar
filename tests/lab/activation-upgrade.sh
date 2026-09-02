#!/bin/bash

# Permanent update-only regression for the v0.1.3 toggle binding and the
# current candidate's ownership-preserving migration to summon activation.

omarchy_host_test() {
  local product_root lab_root plugin_dir shortcut viewport_width viewport_height bar_x bar_y
  product_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
  lab_root="$(cd -- "$product_root/../../omarchy/plugin-lab" && pwd)"
  # shellcheck source=/dev/null
  source "$lab_root/host-tests/helpers/pointer.sh"

  stage_revision() {
    local revision="$1"
    git -C "$product_root" archive "$revision" | ssh_guest \
      "mkdir -p /tmp/news-radar-upgrade-origin && find /tmp/news-radar-upgrade-origin -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf -- {} + && tar -C /tmp/news-radar-upgrade-origin -xf -"
  }

  stage_candidate() {
    tar -C "$product_root" --exclude=.git --exclude=dist --exclude='__pycache__' -cf - . | ssh_guest \
      "find /tmp/news-radar-upgrade-origin -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf -- {} + && tar -C /tmp/news-radar-upgrade-origin -xf -"
  }

  wait_radar() {
    wait_for_guest_state "$1" 15 ssh_session \
      "hyprctl -j activewindow | jq -e '.title == \"📰 Omarchy News Radar\"' && hyprctl -j clients | jq -e '[.[] | select(.title == \"📰 Omarchy News Radar\")] | length == 1'"
  }

  obscure_radar() {
    ssh_session "hyprctl dispatch 'hl.dsp.focus({ window = \"title:Radar Activation Fixture\" })' >/dev/null"
    wait_for_guest_state "ordinary window obscures Radar" 10 ssh_session \
      "hyprctl -j activewindow | jq -e '.title == \"Radar Activation Fixture\"'"
  }

  stage_revision v0.1.3
  ssh_guest "git -C /tmp/news-radar-upgrade-origin init -q && git -C /tmp/news-radar-upgrade-origin add . && git -C /tmp/news-radar-upgrade-origin -c user.name=PluginLab -c user.email=lab@invalid commit -qm v0.1.3"
  ssh_session "omarchy-plugin-add /tmp/news-radar-upgrade-origin --enable --yes" >"$RUN_DIR/news-radar-v013-install.log" || return 1

  # Expanded by the disposable guest, not by this host-side test.
  # shellcheck disable=SC2016
  plugin_dir='$HOME/.config/omarchy/plugins/io.github.mtolhuys.news-radar'
  shortcut="$plugin_dir/bin/news-radar-shortcut"
  wait_for_guest_state "released v0.1.3 is enabled" 20 ssh_session \
    "omarchy-plugin-list --json | jq -e 'any(.[]; .id == \"io.github.mtolhuys.news-radar\" and .enabled == true)' && jq -e '.version == \"0.1.3\"' $plugin_dir/manifest.json" || return 1
  ssh_session "$shortcut install" >"$RUN_DIR/news-radar-v013-shortcut.json" || return 1
  ssh_session "setsid uwsm-app -- xdg-terminal-exec --title='Radar Activation Fixture' -e bash -c 'sleep 180' >/dev/null 2>&1 &" || return 1
  wait_for_guest_state "activation fixture exists" 15 ssh_session \
    "hyprctl -j clients | jq -e 'any(.[]; .title == \"Radar Activation Fixture\")'" || return 1

  viewport_width="$(ssh_session "hyprctl -j monitors | jq -r '.[0].width'")"
  viewport_height="$(ssh_session "hyprctl -j monitors | jq -r '.[0].height'")"
  wait_for_guest_state "v0.1.3 newspaper is visible" 20 ssh_session \
    "omarchy-shell shell debugBarGeometry | jq -e 'any(.[]; .id == \"io.github.mtolhuys.news-radar\" and .visible == true)'" || return 1

  ssh_session "omarchy-shell shell summon io.github.mtolhuys.news-radar"
  wait_radar "v0.1.3 Radar opens" || return 1
  obscure_radar || return 1
  bar_x="$(ssh_session "omarchy-shell shell debugBarGeometry | jq -r '.[] | select(.id == \"io.github.mtolhuys.news-radar\" and .visible == true) | (.x + (.width / 2) | floor)'")"
  bar_y="$(ssh_session "omarchy-shell shell debugBarGeometry | jq -r '.[] | select(.id == \"io.github.mtolhuys.news-radar\" and .visible == true) | (.y + (.height / 2) | floor)'")"
  qmp_pointer_tap "$viewport_width" "$viewport_height" "$bar_x" "$bar_y" left
  wait_for_guest_state "released v0.1.3 bar toggle closes obscured Radar" 10 ssh_session \
    "hyprctl -j clients | jq -e 'all(.[]; .title != \"📰 Omarchy News Radar\")'" || return 1

  ssh_session "omarchy-shell shell summon io.github.mtolhuys.news-radar"
  wait_radar "v0.1.3 Radar reopens" || return 1
  obscure_radar || return 1
  press meta_l-alt-n
  wait_for_guest_state "released v0.1.3 shortcut toggle closes obscured Radar" 10 ssh_session \
    "hyprctl -j clients | jq -e 'all(.[]; .title != \"📰 Omarchy News Radar\")'" || return 1

  stage_candidate
  ssh_guest "git -C /tmp/news-radar-upgrade-origin add -A && git -C /tmp/news-radar-upgrade-origin -c user.name=PluginLab -c user.email=lab@invalid commit -qm candidate"
  ssh_session "omarchy-plugin-update io.github.mtolhuys.news-radar --yes" >"$RUN_DIR/news-radar-candidate-update.log" || return 1
  wait_for_guest_state "candidate replaces plugin source" 20 ssh_session \
    "omarchy-plugin-list --json | jq -e 'any(.[]; .id == \"io.github.mtolhuys.news-radar\" and .enabled == true)' && jq -e '.version == \"0.2.0\"' $plugin_dir/manifest.json && grep -Fq 'shell summon io.github.mtolhuys.news-radar' $plugin_dir/src/BarWidget.qml" || return 1

  wait_for_guest_state "the update alone migrates the exact owned legacy action" 20 ssh_session \
    "$shortcut status | jq -e '.classification == \"owned\"' && grep -Fq 'shell summon io.github.mtolhuys.news-radar' \"\$HOME/.config/hypr/bindings.lua\" && ! grep -Fq 'shell toggle io.github.mtolhuys.news-radar' \"\$HOME/.config/hypr/bindings.lua\" && compgen -G \"\$HOME/.config/hypr/bindings.lua.news-radar-backup-*\" >/dev/null && test -z \"\$(hyprctl configerrors)\" && hyprctl -j clients | jq -e 'all(.[]; .title != \"📰 Omarchy News Radar\")'" || return 1
  ssh_session "$shortcut status" >"$RUN_DIR/news-radar-candidate-updated-shortcut-status.json" || return 1

  press meta_l-alt-n
  wait_radar "update-migrated shortcut opens Radar" || return 1
  obscure_radar || return 1
  press meta_l-alt-n
  wait_radar "update-migrated shortcut raises obscured Radar without closing" || return 1

  obscure_radar || return 1
  bar_x="$(ssh_session "omarchy-shell shell debugBarGeometry | jq -r '.[] | select(.id == \"io.github.mtolhuys.news-radar\" and .visible == true) | (.x + (.width / 2) | floor)'")"
  bar_y="$(ssh_session "omarchy-shell shell debugBarGeometry | jq -r '.[] | select(.id == \"io.github.mtolhuys.news-radar\" and .visible == true) | (.y + (.height / 2) | floor)'")"
  qmp_pointer_tap "$viewport_width" "$viewport_height" "$bar_x" "$bar_y" left
  wait_radar "candidate bar summon raises obscured Radar" || {
    ssh_session "hyprctl -j activewindow; hyprctl -j clients; omarchy-shell shell call io.github.mtolhuys.news-radar debugState ''" >"$RUN_DIR/news-radar-candidate-bar-failure.log" 2>&1 || true
    return 1
  }
  press meta_l-alt-n
  wait_radar "foreground repeat remains one focused Radar window" || return 1

  capture_console "success-news-radar-activation-upgrade"
  ssh_session "$shortcut remove" >"$RUN_DIR/news-radar-candidate-shortcut-removed.json" || return 1
  printf 'ok - the plugin update alone migrated exact legacy ownership; shortcut and bar each raise one obscured Radar window\n'
}
