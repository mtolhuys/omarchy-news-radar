#!/bin/bash

# Revalidates the live default shortcut and the documented personal-override
# order inside a disposable Omarchy guest. This never runs on the host.

omarchy_host_test() {
  local guest_home
  # The literal HOME belongs to the disposable guest.
  # shellcheck disable=SC2016
  guest_home="$(ssh_guest 'printf %s "$HOME"')" || return 1
  [[ -n $guest_home ]] || return 1
  local guest_bindings="$guest_home/.config/hypr/bindings.lua"
  local guest_backup="${guest_bindings}.news-radar-contract-audit"

  ssh_session "hyprctl binds -j" >"$RUN_DIR/news-radar-binds-before.json" || return 1
  jq -e '[.[] | select((.description // "") == "Editor" and ((.key // "") | ascii_upcase) == "N" and .modmask == 65)] | length == 1' \
    "$RUN_DIR/news-radar-binds-before.json" >/dev/null || return 1

  ssh_session "cp --preserve=all '$guest_bindings' '$guest_backup'" || return 1
  trap 'ssh_session "mv -- \"'"'$guest_backup'"'\" \"'"'$guest_bindings'"'\"; hyprctl reload >/dev/null" >/dev/null 2>&1 || true' RETURN

  ssh_session "printf '\n-- Omarchy News Radar contract audit --\nhl.unbind(\"SUPER + SHIFT + N\")\no.bind(\"SUPER + SHIFT + N\", \"News Radar contract audit\", \"true\")\n' >>'$guest_bindings'; hyprctl reload >/dev/null" || return 1
  ssh_session "[[ -z \$(hyprctl configerrors) ]]" || return 1
  ssh_session "hyprctl binds -j" >"$RUN_DIR/news-radar-binds-audit.json" || return 1
  jq -e '[.[] | select((.description // "") == "News Radar contract audit" and ((.key // "") | ascii_upcase) == "N" and .modmask == 65)] | length == 1' \
    "$RUN_DIR/news-radar-binds-audit.json" >/dev/null || return 1
  jq -e '[.[] | select((.description // "") == "Editor" and ((.key // "") | ascii_upcase) == "N" and .modmask == 65)] | length == 0' \
    "$RUN_DIR/news-radar-binds-audit.json" >/dev/null || return 1

  ssh_session "mv -- '$guest_backup' '$guest_bindings'; hyprctl reload >/dev/null" || return 1
  trap - RETURN
  ssh_session "[[ -z \$(hyprctl configerrors) ]]" || return 1
  ssh_session "hyprctl binds -j" >"$RUN_DIR/news-radar-binds-restored.json" || return 1
  jq -e '[.[] | select((.description // "") == "Editor" and ((.key // "") | ascii_upcase) == "N" and .modmask == 65)] | length == 1' \
    "$RUN_DIR/news-radar-binds-restored.json" >/dev/null || return 1

  capture_console "news-radar-contract-audit-restored"
  printf 'ok - exact Super+Shift+N Editor default is live\n'
  printf 'ok - personal override hl.unbind replaces it once and restores cleanly\n'
}
