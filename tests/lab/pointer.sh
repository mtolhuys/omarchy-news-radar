#!/bin/bash

# The compositor can warp its cursor while QEMU's absolute tablet retains the
# last injected coordinate. Move away before each real click so a repeated
# target still generates movement after a shell restart or a focused window.
# This wraps the maintained lab helper without changing the lab checkout.
# shellcheck disable=SC2329
radar_pointer_tap() {
  local width="$1" height="$2" x="$3" y="$4" response away_x away_y
  ((width >= 2 && height >= 2 && x >= 0 && x < width && y >= 0 && y < height)) || return 2
  if ((x < width / 2)); then away_x=32766; else away_x=1; fi
  if ((y < height / 2)); then away_y=32766; else away_y=1; fi
  response="$(qmp "\"input-send-event\", \"id\": \"radar-pointer-nudge\", \"arguments\": {\"events\": [
    {\"type\":\"abs\",\"data\":{\"axis\":\"x\",\"value\":$away_x}},
    {\"type\":\"abs\",\"data\":{\"axis\":\"y\",\"value\":$away_y}}
  ]}")"
  if ! jq -e -s 'any(.[]; .id == "radar-pointer-nudge" and has("return"))' <<<"$response" >/dev/null; then
    printf 'QMP did not acknowledge Radar pointer movement: %s\n' "$response" >&2
    return 1
  fi
  sleep 0.1
  qmp_pointer_tap "$@"
}
