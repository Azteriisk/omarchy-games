#!/usr/bin/env python3
"""
Omarchy Playspace Manager
Marks the active window as the "Active Playspace" (Game Mode).
Confiines focus and cursor, disables idle/sleep, enables immediate tearing mode,
and provides a universal escape mechanism between rounds.
"""

import sys
import os
import json
import subprocess
import argparse
from pathlib import Path

STATE_FILE = Path.home() / ".local" / "state" / "omarchy" / "playspace.json"

def get_active_window():
    try:
        raw = subprocess.check_output(["hyprctl", "activewindow", "-j"], text=True)
        data = json.loads(raw)
        if data and data.get("address"):
            return data
    except Exception:
        pass
    return None

def load_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"active": False}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def notify(summary, body, urgency="normal"):
    try:
        subprocess.Popen([
            "notify-send",
            "-a", "Omarchy Playspace",
            "-i", "input-gaming",
            "-u", urgency,
            summary,
            body
        ])
    except Exception:
        pass

def playspace_on():
    win = get_active_window()
    if not win:
        notify("Playspace Error", "No active window detected to bind.", urgency="critical")
        return

    addr = win["address"]
    title = win.get("title", "Game Window")
    klass = win.get("initialClass") or win.get("class", "Game")
    at = win.get("at", [0, 0])
    size = win.get("size", [1920, 1080])

    center_x = at[0] + (size[0] // 2)
    center_y = at[1] + (size[1] // 2)

    # 1. Hyprland game mode properties
    subprocess.run(["hyprctl", "setprop", f"address:{addr}", "immediate", "1"], capture_output=True)
    subprocess.run(["hyprctl", "setprop", f"address:{addr}", "idleinhibit", "always"], capture_output=True)
    subprocess.run(["hyprctl", "dispatch", "focuswindow", f"address:{addr}"], capture_output=True)
    subprocess.run(["hyprctl", "dispatch", "bringactivetotop"], capture_output=True)

    # 2. Center cursor in active playspace
    subprocess.run(["hyprctl", "dispatch", "movecursor", str(center_x), str(center_y)], capture_output=True)

    # 3. Save state
    state = {
        "active": True,
        "address": addr,
        "title": title,
        "class": klass,
        "at": at,
        "size": size
    }
    save_state(state)

    short_title = title if len(title) <= 30 else title[:27] + "..."
    notify(
        "🎮 Playspace Active",
        f"Locked to <b>{short_title}</b>\nPress <b>Super+Ctrl+G</b> to pause/escape."
    )
    print(f"Playspace active on {short_title} ({addr})")

def playspace_off():
    state = load_state()
    addr = state.get("address")
    if addr:
        subprocess.run(["hyprctl", "setprop", f"address:{addr}", "immediate", "0"], capture_output=True)
        subprocess.run(["hyprctl", "setprop", f"address:{addr}", "idleinhibit", "none"], capture_output=True)

    save_state({"active": False})
    notify(
        "🎮 Playspace Paused",
        "Cursor free. Press <b>Super+Ctrl+G</b> to resume.",
        urgency="low"
    )
    print("Playspace paused (cursor free).")

def playspace_toggle():
    state = load_state()
    if state.get("active"):
        playspace_off()
    else:
        playspace_on()

def playspace_status():
    state = load_state()
    print(json.dumps(state, indent=2))

def main():
    parser = argparse.ArgumentParser(description="Omarchy Playspace Manager")
    parser.add_argument("command", choices=["toggle", "on", "off", "escape", "status"], nargs="?", default="status")
    args = parser.parse_args()

    if args.command == "toggle":
        playspace_toggle()
    elif args.command == "on":
        playspace_on()
    elif args.command in ("off", "escape"):
        playspace_off()
    elif args.command == "status":
        playspace_status()

if __name__ == "__main__":
    main()
