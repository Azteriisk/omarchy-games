#!/usr/bin/env bash
# High-Performance Xbox Cloud Stream Runner for Omarchy Games
# Features hardware VA-API decode, Wayland native surface, and Better xCloud.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROFILE_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/omarchy/xcloud"
EXT_DIR="$PROFILE_DIR/extensions/better-xcloud"

TARGET_URL="https://www.xbox.com/play"
if [[ -n "${1:-}" ]]; then
  if [[ "$1" =~ ^https?:// ]]; then
    TARGET_URL="$1"
  elif [[ "$1" =~ ^launch/ || "$1" =~ ^games/ ]]; then
    TARGET_URL="https://www.xbox.com/play/$1"
  else
    TARGET_URL="https://www.xbox.com/play/launch/$1"
  fi
fi

# Ensure extension unpacked
mkdir -p "$EXT_DIR"
if [[ ! -f "$EXT_DIR/better-xcloud.user.js" && -f "$BASE_DIR/assets/better-xcloud.user.js" ]]; then
  cp "$BASE_DIR/assets/better-xcloud.user.js" "$EXT_DIR/better-xcloud.user.js"
fi
if [[ -f "$SCRIPT_DIR/omarchy-fix.js" ]]; then
  cp "$SCRIPT_DIR/omarchy-fix.js" "$EXT_DIR/omarchy-fix.js"
fi

# Generate manifest if missing
if [[ ! -f "$EXT_DIR/manifest.json" ]]; then
  cat << EOF > "$EXT_DIR/manifest.json"
{
  "manifest_version": 3,
  "name": "Better xCloud for Omarchy",
  "version": "6.7.12",
  "description": "Hardware-accelerated Xbox Cloud streaming runtime",
  "content_scripts": [
    {
      "matches": [
        "https://www.xbox.com/*play*",
        "https://www.xbox.com/*/auth/msa?*loggedIn*"
      ],
      "exclude_matches": [
        "https://www.xbox.com/*/xbox-game-pass/play-day-one"
      ],
      "js": ["omarchy-fix.js", "better-xcloud.user.js"],
      "run_at": "document_start",
      "world": "MAIN"
    }
  ],
  "host_permissions": [
    "https://www.xbox.com/*"
  ]
}
EOF
fi

# Apply tablet isolation to environment
export SDL_GAMECONTROLLER_IGNORE_DEVICES="0x256c/0x006d,0x056a/0x037a,0x28bd/0x0042"

CHROMIUM_BIN=""
for bin in chromium google-chrome-stable brave; do
  if command -v "$bin" >/dev/null 2>&1; then
    CHROMIUM_BIN="$bin"
    break
  fi
done

if [[ -z "$CHROMIUM_BIN" ]]; then
  echo "Error: Chromium or a Chromium-based browser is required." >&2
  exit 1
fi

echo "🎮 Launching Xbox Cloud Stream: $TARGET_URL"

# Pre-grant pointer lock and keyboard lock in profile preferences
PREFS_DIR="$PROFILE_DIR/Default"
mkdir -p "$PREFS_DIR"
PREFS_FILE="$PREFS_DIR/Preferences"
if [[ ! -f "$PREFS_FILE" ]]; then
  echo '{"profile":{"content_settings":{"exceptions":{"pointer_lock":{"https://www.xbox.com,*":{"setting":1}},"keyboard_lock":{"https://www.xbox.com,*":{"setting":1}}}}}}' > "$PREFS_FILE"
fi

# Background process to engage playspace once the window appears
(
  sleep 2
  python3 "$SCRIPT_DIR/playspace.py" on 2>/dev/null || true
) &

exec "$CHROMIUM_BIN" \
  --app="$TARGET_URL" \
  --class="omarchy-game" \
  --user-data-dir="$PROFILE_DIR" \
  --ozone-platform=wayland \
  --enable-features=VaapiVideoDecoder,VaapiVideoDecodeLinuxGL,UseOzonePlatform,PointerLockOptions \
  --disable-features=Translate,EyeDropper \
  --disable-pinch \
  --autoplay-policy=no-user-gesture-required \
  --load-extension="$EXT_DIR" \
  "$@"
