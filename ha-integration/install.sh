#!/bin/bash
set -e
BASE="https://raw.githubusercontent.com/f1yaw4y/nanoclaw/main/ha-integration/custom_components/nanoclaw"
DEST="/config/custom_components/nanoclaw"

mkdir -p "$DEST/translations"
for f in __init__.py manifest.json const.py config_flow.py conversation.py strings.json; do
  curl -fsSL "$BASE/$f" -o "$DEST/$f"
done
curl -fsSL "$BASE/translations/en.json" -o "$DEST/translations/en.json"
echo "NanoClaw integration installed. Restart Home Assistant to load it."
