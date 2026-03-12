#!/bin/bash
set -e
REPO="https://raw.githubusercontent.com/f1yaw4y/nanoclaw/main/ha-integration/custom_components"

install_component() {
  local name="$1"
  local dest="/config/custom_components/$name"
  local base="$REPO/$name"
  mkdir -p "$dest/translations"
  for f in __init__.py manifest.json const.py config_flow.py conversation.py strings.json; do
    curl -fsSL "$base/$f" -o "$dest/$f"
  done
  curl -fsSL "$base/translations/en.json" -o "$dest/translations/en.json"
  echo "$name installed."
}

install_component nanoclaw
install_component venice_ai
echo "All integrations installed. Restart Home Assistant to load them."
