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

echo "🎮 Installing Omarchy Games plugin ($PLUGIN_ID)..."

# 1. Ensure plugins directory exists
mkdir -p "$PLUGINS_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$CONFIG_DIR"

# 2. If running outside plugins dir, copy files
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
fi

# 3. Ensure scripts are executable & symlink CLI
chmod +x "$TARGET_DIR/scripts/omarchy-games"
chmod +x "$TARGET_DIR/scripts/games_scanner.py"
ln -sf "$TARGET_DIR/scripts/omarchy-games" "$CLI_TARGET"
echo "  ✓ Symlinked omarchy-games to $CLI_TARGET"

# 4. Initialize config file if not present
if [[ ! -f "$CONFIG_FILE" ]]; then
  cp "$TARGET_DIR/config.default.json" "$CONFIG_FILE"
  echo "  ✓ Created default games configuration at $CONFIG_FILE"
fi

# 5. Configure shell.json to register azterisk.games in plugins[]
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

# 6. Perform initial games scan & update Omarchy Menu
echo "  🔎 Scanning game libraries & generating 'Games' menu..."
"$CLI_TARGET" sync

# 7. Reload Omarchy shell
if command -v omarchy >/dev/null 2>&1; then
  echo "  ✓ Reloading Omarchy shell..."
  omarchy restart shell 2>/dev/null || true
elif command -v omarchy-shell >/dev/null 2>&1; then
  omarchy-shell shell rescanPlugins 2>/dev/null || true
fi

echo ""
echo "======================================================================"
echo "  🎮 Omarchy Games installed successfully!"
echo "======================================================================"
echo "  Features:"
echo "    • Open Omarchy Menu (SUPER+ALT+SPACE or click menu logo):"
echo "      - Click 'Apps' -> 'Games' to view all your installed games!"
echo "      - Type in the search bar: games are indexed and instantly launchable!"
echo "    • Multi-source support: Steam, Lutris, RetroArch, & Custom."
echo "    • CLI utility: run 'omarchy-games --help' in terminal."
echo "    • Optional top-bar widget available: 'azterisk.games'"
echo "======================================================================"
