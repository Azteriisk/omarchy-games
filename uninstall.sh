#!/usr/bin/env bash
# Uninstaller for Omarchy Games (azterisk.games)
# Author: Azteriisk

set -euo pipefail

PLUGIN_ID="azterisk.games"
PLUGINS_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/plugins"
TARGET_DIR="$PLUGINS_DIR/$PLUGIN_ID"
BIN_DIR="$HOME/.local/bin"
CLI_TARGET="$BIN_DIR/omarchy-games"
SHELL_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/shell.json"

echo "🗑 Uninstalling Omarchy Games plugin ($PLUGIN_ID)..."

# 1. Clean games from user menu
if [[ -f "$TARGET_DIR/scripts/games_scanner.py" ]]; then
  echo "  ✓ Cleaning Games from Omarchy Menu..."
  python3 "$TARGET_DIR/scripts/games_scanner.py" --clean || true
elif command -v omarchy-games >/dev/null 2>&1; then
  omarchy-games clean || true
fi

# 2. Remove CLI symlink
if [[ -L "$CLI_TARGET" || -f "$CLI_TARGET" ]]; then
  rm -f "$CLI_TARGET"
  echo "  ✓ Removed CLI binary: $CLI_TARGET"
fi

# 3. Remove plugin folder
if [[ -d "$TARGET_DIR" ]]; then
  rm -rf "$TARGET_DIR"
  echo "  ✓ Removed plugin directory: $TARGET_DIR"
fi

# 4. Remove from shell.json
if [[ -f "$SHELL_CONFIG" ]]; then
  echo "  ⚙ Updating shell.json..."
  python3 - << 'PYEOF'
import json
from pathlib import Path

shell_file = Path.home() / ".config" / "omarchy" / "shell.json"
try:
    with open(shell_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "plugins" in data and isinstance(data["plugins"], list):
        data["plugins"] = [p for p in data["plugins"] if not (isinstance(p, dict) and p.get("id") == "azterisk.games")]

    with open(shell_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print("     [OK] azterisk.games removed from shell.json")
except Exception as err:
    print(f"     [WARN] Could not update shell.json: {err}")
PYEOF
fi

# 5. Reload Omarchy shell
if command -v omarchy >/dev/null 2>&1; then
  echo "  ✓ Reloading Omarchy shell..."
  omarchy restart shell 2>/dev/null || true
elif command -v omarchy-shell >/dev/null 2>&1; then
  omarchy-shell shell rescanPlugins 2>/dev/null || true
fi

echo ""
echo "======================================================================"
echo "  Omarchy Games uninstalled cleanly."
echo "======================================================================"
