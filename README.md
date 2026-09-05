# Omarchy Games (`azterisk.games`)

> Unified game library manager and launcher for the **Omarchy Desktop Shell**. Indexes games across **Steam**, **Lutris**, **RetroArch**, and custom game sources directly into a dedicated **"Games"** folder on the root menu under **"Apps"**, with real game artwork/icons, full search bar indexability, and quick launch integration.

---

## Features

- **Root Menu "Games" Folder**: Adds an interactive `Games` submenu directly on the main Omarchy Menu (`SUPER + ALT + SPACE`), positioned right below `Apps`!
- **Dynamic Game Artwork**: Automatically discovers real game icons from Steam's library cache and Lutris's cover art/banners! Generic gamepad glyphs (`󰊴`) are preserved as graceful fallbacks for special cases where no artwork exists.
- **Full Search Bar Indexing**: Type any game title into the Omarchy Menu search bar ("Go..."): matches are instantly surfaced with the breadcrumb `Games` and launch immediately on Enter.
- **Multi-Source Detection**:
  - **Steam**: Automatic discovery of all Steam libraries (internal storage, secondary internal drives, and external removable drives like `/run/media/.../SteamLibrary`). Filters out Proton/tool runtimes while preserving all your games.
  - **Lutris**: Reads SQLite `pga.db` and YAML game definitions. Launches with `uwsm-app -- lutris lutris:rungame/<slug>`.
  - **RetroArch**: Supports `.lpl` JSON playlists for retro titles and emulation.
  - **Custom Games**: Easily add standalone Linux binaries, Wine prefixes, or script launchers.
- **Background Quickshell Service**: `Service.qml` runs in `omarchy-shell` to auto-sync on startup and periodically rescan for new installs.
- **Top Bar Widget**: Optional `azterisk.games` widget with gamepad glyph (`󰊴`), live game counter, left-click to open Games menu, and right-click quick actions.
- **CLI Utility (`omarchy-games`)**: Fast terminal management for rescanning, listing, launching, and configuring sources.

---

## Installation

Run the all-in-one installer:

```bash
cd ~/Projects/omarchy-games
./install.sh
```

The installer will:
1. Copy the plugin files to `~/.config/omarchy/plugins/azterisk.games/`.
2. Symlink the CLI tool to `~/.local/bin/omarchy-games`.
3. Initialize `~/.config/omarchy/games/config.json`.
4. Register the plugin service in `~/.config/omarchy/shell.json`.
5. Run the initial games scan to populate the Omarchy Menu.
6. Reload the Omarchy shell.

---

## Usage

### In the Omarchy Menu
1. Press `SUPER + ALT + SPACE` (or click the Omarchy logo in the top bar).
2. The **"Games"** folder is right on the main menu, directly under **"Apps"**!
3. Click **"Games"** to browse your full gaming library with rich artwork icons.
4. Or simply start typing any game name (e.g. `Elden`, `Black Ops`, `Valheim`, `CS2`) into the search bar: press Enter to play!
5. Inside the Games folder, click **"Rescan Game Libraries"** anytime you install new games to update the list instantly.

### Quick Launch Direct Shortcut (Optional)
You can bind a direct hotkey to open the Games folder immediately in `~/.config/hypr/bindings.lua`:
```lua
o.bind("SUPER", "g", "Games menu", "omarchy-menu summon games")
```

### CLI Commands
```bash
# Rescan all game libraries and update menu
omarchy-games sync

# List all discovered games and sources
omarchy-games list

# View detected library folders and source status
omarchy-games sources

# Interactive game launcher (uses fzf if installed)
omarchy-games launch

# Launch specific game by title
omarchy-games launch "Elden Ring"

# Open configuration in your editor
omarchy-games config

# Add an extra Steam library or RetroArch playlist directory
omarchy-games add-source steam /path/to/SteamLibrary
```

---

## Configuration (`~/.config/omarchy/games/config.json`)

```json
{
  "sources": {
    "steam": {
      "enabled": true,
      "steam_dir": "~/.local/share/Steam",
      "auto_discover_libraries": true,
      "extra_libraries": [],
      "filter_tools": true,
      "exclude_names": [
        "Steam Linux Runtime*",
        "Proton*",
        "Steamworks*",
        "SteamVR*",
        "Wallpaper Engine",
        "Blender",
        "Aseprite"
      ],
      "launch_wrapper": "uwsm-app -- steam steam://rungameid/{appid}"
    },
    "lutris": {
      "enabled": true,
      "db_path": "~/.local/share/lutris/pga.db",
      "launch_wrapper": "uwsm-app -- lutris lutris:rungame/{slug}"
    },
    "retroarch": {
      "enabled": true,
      "playlist_dir": "~/.config/retroarch/playlists",
      "launch_wrapper": "uwsm-app -- retroarch -L \"{core_path}\" \"{rom_path}\""
    },
    "custom": {
      "enabled": true,
      "games": []
    }
  },
  "ui": {
    "folder_label": "Games",
    "folder_icon": "󰊴",
    "folder_aliases": ["game", "games", "gaming", "steam", "lutris"],
    "steam_icon": "󰓓",
    "lutris_icon": "󰊴",
    "retroarch_icon": "󰊱",
    "show_rescan_action": true,
    "show_config_action": true,
    "show_source_in_description": true
  }
}
```

---

## Uninstallation

To cleanly remove the plugin, menu entries, and configuration:

```bash
cd ~/Projects/omarchy-games
./uninstall.sh
```
