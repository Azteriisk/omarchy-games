#!/usr/bin/env bash
# Complete All-In-One Installer for Omarchy Games (azterisk.games)
# Author: Azteriisk

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ID="azterisk.games"
PLUGINS_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/plugins"
TARGET_DIR="$PLUGINS_DIR/$PLUGIN_ID"
BIN_DIR="$HOME/.local/bin"
CLI_TARGET="$BIN_DIR/omarchy-games"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/games"
CONFIG_FILE="$CONFIG_DIR/config.json"
SHELL_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/shell.json"

echo "🎮 Installing Omarchy Games & Playspace plugin ($PLUGIN_ID)..."

# 1. Ensure directories exist
mkdir -p "$PLUGINS_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$CONFIG_DIR"

# 2. Copy files into user plugins dir
if [ "$SCRIPT_DIR" != "$TARGET_DIR" ]; then
  mkdir -p "$TARGET_DIR"
  cp -a "$SCRIPT_DIR/manifest.json" \
        "$SCRIPT_DIR/Service.qml" \
        "$SCRIPT_DIR/BarWidget.qml" \
        "$SCRIPT_DIR/config.default.json" \
        "$SCRIPT_DIR/scripts" \
        "$SCRIPT_DIR/install.sh" \
        "$SCRIPT_DIR/uninstall.sh" \
        "$SCRIPT_DIR/README.md" "$TARGET_DIR/"
  if [ -d "$SCRIPT_DIR/assets" ]; then
    cp -a "$SCRIPT_DIR/assets" "$TARGET_DIR/"
  fi
fi

# 3. Ensure scripts are executable & symlink CLI
chmod +x "$TARGET_DIR/scripts/"*
ln -sf "$TARGET_DIR/scripts/omarchy-games" "$CLI_TARGET"
echo "  ✓ Symlinked omarchy-games to $CLI_TARGET"

# 4. Initialize config file if not present
if [[ ! -f "$CONFIG_FILE" ]]; then
  cp "$TARGET_DIR/config.default.json" "$CONFIG_FILE"
  echo "  ✓ Created default games configuration at $CONFIG_FILE"
fi

# 5. Apply Gamepad Steward tablet isolation
"$CLI_TARGET" controller fix >/dev/null 2>&1 || true
echo "  ✓ Applied Gamepad Steward tablet isolation"

# 6. Configure shell.json to register azterisk.games in plugins[]
if [[ -f "$SHELL_CONFIG" ]]; then
  echo "  ⚙ Configuring shell.json for azterisk.games service..."
  python3 - << 'PYEOF'
import json
from pathlib import Path

shell_file = Path.home() / ".config" / "omarchy" / "shell.json"
try:
    with open(shell_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "plugins" not in data or not isinstance(data["plugins"], list):
        data["plugins"] = []

    has_plugin = any(isinstance(p, dict) and p.get("id") == "azterisk.games" for p in data["plugins"])
    if not has_plugin:
        data["plugins"].append({"id": "azterisk.games"})

    with open(shell_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print("     [OK] shell.json updated successfully")
except Exception as err:
    print(f"     [WARN] Could not update shell.json: {err}")
PYEOF
fi

# 7. Perform initial games scan & update Omarchy Menu
echo "  🔎 Scanning game libraries & generating 'Games' menu..."
"$CLI_TARGET" sync

# 8. Reload Omarchy shell plugins
if command -v omarchy-shell >/dev/null 2>&1; then
  echo "  ✓ Reloading Omarchy shell plugins..."
  omarchy-shell shell rescanPlugins 2>/dev/null || true
fi

echo ""
echo "======================================================================"
echo "  🎮 Omarchy Games & Playspace installed successfully!"
echo "======================================================================"
echo "  Features:"
echo "    • Open Omarchy Menu (SUPER+ALT+SPACE or click menu logo):"
echo "      - Click 'Games' to view all your installed Steam, Lutris, & xCloud games!"
echo "    • Active Playspace:"
echo "      - Press SUPER+CTRL+G to engage/escape Playspace on any game window."
echo "    • Controller Steward:"
echo "      - Isolates Huion/Wacom drawing tablets so gamepads stay at Slot 0."
echo "      - Test controller anytime: 'omarchy-games controller test'"
echo "    • Xbox Cloud Stream:"
echo "      - Run 'omarchy-games stream xbox' for hardware VA-API streaming."
echo "======================================================================"
