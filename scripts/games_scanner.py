#!/usr/bin/env python3
"""
Omarchy Games Scanner
Multi-source game indexing engine for Omarchy.
Discovers Steam, Lutris, RetroArch, and custom games, and generates
the "Games" folder entries for the Omarchy Menu.
"""

import sys
import os
import glob
import re
import json
import fnmatch
import sqlite3
import subprocess
from pathlib import Path

# Default Paths
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "omarchy" / "games" / "config.json"
USER_MENU_PATH = Path.home() / ".config" / "omarchy" / "extensions" / "omarchy-menu.jsonc"
SCRIPT_DIR = Path(__file__).resolve().parent
FALLBACK_CONFIG = SCRIPT_DIR.parent / "config.default.json"

BEGIN_MARKER = "// --- BEGIN OMARCHY GAMES (AUTO-GENERATED) ---"
END_MARKER = "// --- END OMARCHY GAMES ---"

def load_config():
    cfg = {}
    if DEFAULT_CONFIG_PATH.is_file():
        try:
            with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception as e:
            print(f"[WARN] Error reading {DEFAULT_CONFIG_PATH}: {e}", file=sys.stderr)
    elif FALLBACK_CONFIG.is_file():
        try:
            with open(FALLBACK_CONFIG, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            pass

    # Ensure sections exist with defaults
    sources = cfg.setdefault("sources", {})
    steam = sources.setdefault("steam", {})
    steam.setdefault("enabled", True)
    steam.setdefault("steam_dir", "~/.local/share/Steam")
    steam.setdefault("auto_discover_libraries", True)
    steam.setdefault("extra_libraries", [])
    steam.setdefault("filter_tools", True)
    steam.setdefault("exclude_names", [
        "Steam Linux Runtime*", "Proton*", "Steamworks*", "SteamVR*",
        "Wallpaper Engine", "Blender", "Aseprite"
    ])
    steam.setdefault("launch_wrapper", "uwsm-app -- steam steam://rungameid/{appid}")

    lutris = sources.setdefault("lutris", {})
    lutris.setdefault("enabled", True)
    lutris.setdefault("db_path", "~/.local/share/lutris/pga.db")
    lutris.setdefault("launch_wrapper", "uwsm-app -- lutris lutris:rungame/{slug}")

    retroarch = sources.setdefault("retroarch", {})
    retroarch.setdefault("enabled", True)
    retroarch.setdefault("playlist_dir", "~/.config/retroarch/playlists")
    retroarch.setdefault("launch_wrapper", "uwsm-app -- retroarch -L \"{core_path}\" \"{rom_path}\"")

    custom = sources.setdefault("custom", {})
    custom.setdefault("enabled", True)
    custom.setdefault("games", [])

    ui = cfg.setdefault("ui", {})
    ui.setdefault("folder_label", "Games")
    ui.setdefault("folder_icon", "󰊴")
    ui.setdefault("folder_aliases", ["game", "games", "gaming", "steam", "lutris", "retroarch"])
    ui.setdefault("steam_icon", "󰓓")
    ui.setdefault("lutris_icon", "󰊴")
    ui.setdefault("retroarch_icon", "󰊱")
    ui.setdefault("custom_icon", "󰊴")
    ui.setdefault("show_rescan_action", True)
    ui.setdefault("show_config_action", True)
    ui.setdefault("show_source_in_description", True)

    return cfg

def parse_acf(path):
    data = {}
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        for match in re.finditer(r'"(\w+)"\s+"([^"]*)"', content):
            data[match.group(1)] = match.group(2)
    except Exception:
        pass
    return data

def find_steam_libraries(steam_dir_str, auto_discover=True, extra_libs=None):
    libs = set()
    base_steam = Path(os.path.expanduser(steam_dir_str)).resolve()
    if base_steam.is_dir():
        libs.add(base_steam)

    alt_steam = Path.home() / ".steam" / "steam"
    if alt_steam.is_dir():
        libs.add(alt_steam.resolve())

    if auto_discover:
        for steam_root in list(libs):
            vdf_path = steam_root / "steamapps" / "libraryfolders.vdf"
            if vdf_path.is_file():
                try:
                    with open(vdf_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    for match in re.finditer(r'"path"\s+"([^"]+)"', content):
                        p = Path(match.group(1).replace("\\\\", "/")).resolve()
                        if p.is_dir():
                            libs.add(p)
                except Exception:
                    pass

    if extra_libs:
        for extra in extra_libs:
            p = Path(os.path.expanduser(extra)).resolve()
            if p.is_dir():
                libs.add(p)

    return sorted(list(libs), key=lambda x: str(x))

def scan_steam(cfg):
    steam_cfg = cfg["sources"]["steam"]
    if not steam_cfg.get("enabled", True):
        return []

    games = []
    steam_dir = steam_cfg.get("steam_dir", "~/.local/share/Steam")
    auto_discover = steam_cfg.get("auto_discover_libraries", True)
    extra_libs = steam_cfg.get("extra_libraries", [])
    exclude_patterns = steam_cfg.get("exclude_names", [])
    launch_wrapper = steam_cfg.get("launch_wrapper", "uwsm-app -- steam steam://rungameid/{appid}")
    steam_icon = cfg["ui"].get("steam_icon", "󰓓")
    show_source = cfg["ui"].get("show_source_in_description", True)

    libraries = find_steam_libraries(steam_dir, auto_discover, extra_libs)
    seen_appids = set()

    for lib in libraries:
        manifest_dir = lib / "steamapps"
        if not manifest_dir.is_dir():
            continue
        for m in manifest_dir.glob("appmanifest_*.acf"):
            info = parse_acf(m)
            appid = info.get("appid", "").strip()
            name = info.get("name", "").strip()
            if not appid or not name:
                continue
            if appid in seen_appids:
                continue

            # Check exclusions
            excluded = False
            for pat in exclude_patterns:
                if fnmatch.fnmatch(name, pat):
                    excluded = True
                    break
            if excluded:
                continue

            seen_appids.add(appid)
            action = launch_wrapper.replace("{appid}", appid)
            desc = "Steam · Installed" if show_source else "Installed"

            # Create searchable aliases
            clean_name = re.sub(r'[^a-zA-Z0-9\s]', ' ', name.lower())
            words = clean_name.split()
            aliases = ["steam", name.lower(), clean_name]
            if len(words) > 1:
                acronym = "".join(w[0] for w in words if w)
                if len(acronym) >= 2:
                    aliases.append(acronym)
            if "counter" in words and "strike" in words:
                aliases.extend(["cs", "cs2", "cs 2", "counter strike"])
            if "call" in words and "duty" in words:
                aliases.extend(["cod", "bo2", "t6"])

            games.append({
                "id": f"apps.games.steam-{appid}",
                "label": name,
                "icon": steam_icon,
                "description": desc,
                "aliases": list(dict.fromkeys(aliases)),
                "action": action,
                "source": "steam",
                "raw_id": appid,
                "library": str(lib)
            })

    return games

def scan_lutris(cfg):
    lutris_cfg = cfg["sources"]["lutris"]
    if not lutris_cfg.get("enabled", True):
        return []

    games = []
    db_path = Path(os.path.expanduser(lutris_cfg.get("db_path", "~/.local/share/lutris/pga.db")))
    launch_wrapper = lutris_cfg.get("launch_wrapper", "uwsm-app -- lutris lutris:rungame/{slug}")
    lutris_icon = cfg["ui"].get("lutris_icon", "󰊴")
    show_source = cfg["ui"].get("show_source_in_description", True)

    if db_path.is_file():
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cur = conn.cursor()
            cur.execute("SELECT id, name, slug, runner, installed FROM games WHERE installed = 1")
            for row in cur.fetchall():
                gid, name, slug, runner, installed = row
                if not name or not slug:
                    continue
                runner_str = (runner or "wine").capitalize()
                desc = f"Lutris · {runner_str}" if show_source else runner_str
                action = launch_wrapper.replace("{slug}", slug).replace("{id}", str(gid))

                clean_name = re.sub(r'[^a-zA-Z0-9\s]', ' ', name.lower())
                words = clean_name.split()
                aliases = ["lutris", name.lower(), slug.replace("-", " "), clean_name]
                if len(words) > 1:
                    acronym = "".join(w[0] for w in words if w)
                    if len(acronym) >= 2:
                        aliases.append(acronym)
                if "call" in words and "duty" in words:
                    aliases.extend(["cod", "bo2", "black ops", "t6"])

                games.append({
                    "id": f"apps.games.lutris-{slug}",
                    "label": name,
                    "icon": lutris_icon,
                    "description": desc,
                    "aliases": list(dict.fromkeys(aliases)),
                    "action": action,
                    "source": "lutris",
                    "raw_id": slug,
                    "runner": runner_str
                })
            conn.close()
        except Exception as e:
            print(f"[WARN] Error scanning Lutris database: {e}", file=sys.stderr)

    return games

def scan_retroarch(cfg):
    ra_cfg = cfg["sources"]["retroarch"]
    if not ra_cfg.get("enabled", True):
        return []

    games = []
    playlist_dir = Path(os.path.expanduser(ra_cfg.get("playlist_dir", "~/.config/retroarch/playlists")))
    launch_wrapper = ra_cfg.get("launch_wrapper", 'uwsm-app -- retroarch -L "{core_path}" "{rom_path}"')
    ra_icon = cfg["ui"].get("retroarch_icon", "󰊱")
    show_source = cfg["ui"].get("show_source_in_description", True)

    if not playlist_dir.is_dir():
        flatpak_dir = Path.home() / ".var" / "app" / "org.libretro.RetroArch" / "config" / "retroarch" / "playlists"
        if flatpak_dir.is_dir():
            playlist_dir = flatpak_dir

    if playlist_dir.is_dir():
        for lpl_file in playlist_dir.glob("*.lpl"):
            try:
                with open(lpl_file, "r", encoding="utf-8", errors="ignore") as f:
                    data = json.load(f)
                items = data.get("items", [])
                system_name = lpl_file.stem
                for item in items:
                    label = item.get("label", "").strip()
                    rom_path = item.get("path", "").strip()
                    core_path = item.get("core_path", "DETECT").strip()
                    core_name = item.get("core_name", system_name).strip()
                    if not label or not rom_path:
                        continue

                    slug = re.sub(r'[^a-zA-Z0-9]+', '-', label.lower()).strip("-")
                    game_id = f"apps.games.ra-{slug}"
                    action = launch_wrapper.replace("{core_path}", core_path).replace("{rom_path}", rom_path)
                    desc = f"RetroArch · {core_name}" if show_source else core_name

                    aliases = ["retroarch", label.lower(), system_name.lower()]

                    games.append({
                        "id": game_id,
                        "label": label,
                        "icon": ra_icon,
                        "description": desc,
                        "aliases": list(dict.fromkeys(aliases)),
                        "action": action,
                        "source": "retroarch",
                        "raw_id": rom_path,
                        "system": system_name
                    })
            except Exception as e:
                print(f"[WARN] Error parsing RetroArch playlist {lpl_file}: {e}", file=sys.stderr)

    return games

def scan_custom(cfg):
    custom_cfg = cfg["sources"]["custom"]
    if not custom_cfg.get("enabled", True):
        return []

    games = []
    custom_icon = cfg["ui"].get("custom_icon", "󰊴")
    for item in custom_cfg.get("games", []):
        name = item.get("name", "").strip()
        action = item.get("action", "").strip()
        if not name or not action:
            continue
        slug = re.sub(r'[^a-zA-Z0-9]+', '-', name.lower()).strip("-")
        icon = item.get("icon", custom_icon)
        desc = item.get("description", "Custom Game")
        aliases = ["game", name.lower()]
        if "aliases" in item and isinstance(item["aliases"], list):
            aliases.extend(item["aliases"])

        games.append({
            "id": f"apps.games.custom-{slug}",
            "label": name,
            "icon": icon,
            "description": desc,
            "aliases": list(dict.fromkeys(aliases)),
            "action": action,
            "source": "custom",
            "raw_id": slug
        })

    return games

def scan_all_games(cfg):
    all_games = []
    all_games.extend(scan_steam(cfg))
    all_games.extend(scan_lutris(cfg))
    all_games.extend(scan_retroarch(cfg))
    all_games.extend(scan_custom(cfg))
    all_games.sort(key=lambda g: g["label"].lower())
    return all_games

def generate_games_jsonc_block(cfg, games):
    ui = cfg["ui"]
    folder_label = ui.get("folder_label", "Games")
    folder_icon = ui.get("folder_icon", "󰊴")
    folder_aliases = ui.get("folder_aliases", ["games", "gaming"])
    show_rescan = ui.get("show_rescan_action", True)
    show_config = ui.get("show_config_action", True)

    lines = []
    lines.append(f"  {BEGIN_MARKER}")
    lines.append("  // Games folder under Apps")
    folder_obj = {
        "icon": folder_icon,
        "label": folder_label,
        "aliases": folder_aliases
    }
    lines.append(f'  "apps.games": {json.dumps(folder_obj, ensure_ascii=False)},')
    lines.append("")

    lines.append(f"  // Indexed games ({len(games)} found)")
    for g in games:
        entry = {
            "icon": g["icon"],
            "label": g["label"],
            "description": g["description"],
            "aliases": g["aliases"],
            "action": g["action"]
        }
        lines.append(f'  "{g["id"]}": {json.dumps(entry, ensure_ascii=False)},')

    if show_rescan:
        lines.append("")
        rescan_entry = {
            "icon": "",
            "label": "Rescan Game Libraries",
            "description": "Refresh Steam, Lutris & RetroArch games",
            "aliases": ["rescan", "refresh", "sync-games"],
            "action": "omarchy-games sync && notify-send -i input-gaming 'Omarchy Games' 'Game library rescanned successfully!'"
        }
        lines.append(f'  "apps.games._rescan": {json.dumps(rescan_entry, ensure_ascii=False)},')

    if show_config:
        config_entry = {
            "icon": "󰊴",
            "label": "Game Sources",
            "description": "Configure game libraries and paths",
            "aliases": ["game-sources", "steam-config", "lutris-config"],
            "action": "omarchy-games config"
        }
        lines.append(f'  "setup.games": {json.dumps(config_entry, ensure_ascii=False)},')

    lines.append(f"  {END_MARKER}")
    return "\n".join(lines)

def update_user_menu(cfg, games):
    block = generate_games_jsonc_block(cfg, games)

    existing_content = ""
    USER_MENU_PATH.parent.mkdir(parents=True, exist_ok=True)
    if USER_MENU_PATH.is_file():
        try:
            with open(USER_MENU_PATH, "r", encoding="utf-8") as f:
                existing_content = f.read()
        except Exception:
            existing_content = ""

    if not existing_content.strip():
        # New clean file
        new_content = "{\n" + block + "\n}\n"
    elif BEGIN_MARKER in existing_content and END_MARKER in existing_content:
        # Replace between markers
        before = existing_content[:existing_content.index(BEGIN_MARKER)].rstrip()
        after = existing_content[existing_content.index(END_MARKER) + len(END_MARKER):].lstrip()
        new_content = before + "\n" + block + "\n" + after
    else:
        # Inject before final closing brace
        last_brace = existing_content.rfind("}")
        if last_brace != -1:
            before = existing_content[:last_brace].rstrip()
            # If before doesn't end with a comma, add one if there are non-comment tokens
            non_empty_before = re.sub(r'//.*', '', before).strip()
            if non_empty_before and non_empty_before != "{":
                if not before.endswith(","):
                    before += ","
            new_content = before + "\n" + block + "\n" + existing_content[last_brace:]
        else:
            new_content = "{\n" + block + "\n}\n"

    # Write file atomically
    tmp_path = USER_MENU_PATH.with_suffix(".jsonc.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    tmp_path.replace(USER_MENU_PATH)

    # Signal omarchy menu to reload if available
    try:
        subprocess.run(["omarchy-menu", "refresh"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
    except Exception:
        try:
            subprocess.run(["omarchy", "menu", "refresh"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
        except Exception:
            pass

    return True

def clean_user_menu():
    """Remove games block from user menu upon uninstall."""
    if not USER_MENU_PATH.is_file():
        return
    try:
        with open(USER_MENU_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        if BEGIN_MARKER in content and END_MARKER in content:
            before = content[:content.index(BEGIN_MARKER)].rstrip()
            after = content[content.index(END_MARKER) + len(END_MARKER):].lstrip()
            # Clean up trailing comma if before now ends with comma and after is '}'
            clean_before = re.sub(r',\s*$', '', before)
            new_content = clean_before + "\n" + after
            with open(USER_MENU_PATH, "w", encoding="utf-8") as f:
                f.write(new_content)
            try:
                subprocess.run(["omarchy-menu", "refresh"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
            except Exception:
                pass
    except Exception as e:
        print(f"[WARN] Error cleaning user menu: {e}", file=sys.stderr)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Omarchy Games Scanner")
    parser.add_argument("--sync", action="store_true", help="Scan sources and update Omarchy menu")
    parser.add_argument("--clean", action="store_true", help="Remove games block from Omarchy menu (uninstall)")
    parser.add_argument("--dry-run", action="store_true", help="Scan and print detected games without updating files")
    parser.add_argument("--json", action="store_true", help="Output scanned games as JSON")
    parser.add_argument("--list", action="store_true", help="Output formatted list of detected games")
    parser.add_argument("--sources", action="store_true", help="List detected game sources and paths")
    args = parser.parse_args()

    cfg = load_config()

    if args.clean:
        clean_user_menu()
        print("[OK] Omarchy Games removed from user menu.")
        return 0

    games = scan_all_games(cfg)

    if args.sources:
        print("=== CONFIGURED / DETECTED SOURCES ===")
        steam_cfg = cfg["sources"]["steam"]
        print(f"Steam (enabled: {steam_cfg.get('enabled')})")
        libs = find_steam_libraries(steam_cfg.get("steam_dir", "~/.local/share/Steam"),
                                    steam_cfg.get("auto_discover_libraries", True),
                                    steam_cfg.get("extra_libraries", []))
        for lib in libs:
            print(f"  • Library: {lib}")

        lutris_cfg = cfg["sources"]["lutris"]
        print(f"\nLutris (enabled: {lutris_cfg.get('enabled')})")
        db_path = Path(os.path.expanduser(lutris_cfg.get("db_path", "~/.local/share/lutris/pga.db")))
        print(f"  • Database: {db_path} (exists: {db_path.is_file()})")

        ra_cfg = cfg["sources"]["retroarch"]
        print(f"\nRetroArch (enabled: {ra_cfg.get('enabled')})")
        ra_dir = Path(os.path.expanduser(ra_cfg.get("playlist_dir", "~/.config/retroarch/playlists")))
        print(f"  • Playlists: {ra_dir} (exists: {ra_dir.is_dir()})")
        return 0

    if args.json:
        print(json.dumps(games, indent=2, ensure_ascii=False))
        return 0

    if args.list:
        print(f"Total Games Indexed: {len(games)}")
        print("-" * 60)
        for g in games:
            src = g["source"].upper()
            print(f"[{src:<8}] {g['label']} ({g['description']})")
        return 0

    if args.dry_run:
        print(f"[DRY-RUN] Scanned {len(games)} games:")
        for g in games:
            print(f"  {g['icon']} {g['label']} [{g['source']}] -> {g['action']}")
        return 0

    # Default to sync
    update_user_menu(cfg, games)
    print(f"[OK] Successfully indexed {len(games)} games into Omarchy Menu under 'Apps > Games'.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
