#!/usr/bin/env python3
"""
Omarchy Controller Steward
Detects gamepads, distinguishes real gaming controllers from drawing tablets
(Huion, Wacom, XP-Pen), manages Slot 0 priority, and provides live testing.
"""

import sys
import os
import re
import json
import time
import argparse
from pathlib import Path

TABLET_PATTERNS = re.compile(
    r"tablet|monitor pad|touch strip|dial|stylus|pen|huion|wacom|xp-pen",
    re.IGNORECASE
)

KNOWN_TABLET_VENDORS = {
    0x256c: "Huion",
    0x056a: "Wacom",
    0x28bd: "XP-Pen",
}

def get_evdev():
    try:
        import evdev
        return evdev
    except ImportError:
        return None

def scan_devices():
    evdev = get_evdev()
    devices = []
    
    if evdev is not None:
        try:
            device_paths = evdev.list_devices()
            for path in device_paths:
                try:
                    dev = evdev.InputDevice(path)
                    caps = dev.capabilities()
                    has_keys = evdev.ecodes.EV_KEY in caps
                    has_abs = evdev.ecodes.EV_ABS in caps
                    key_codes = caps.get(evdev.ecodes.EV_KEY, []) if has_keys else []
                    
                    # Check for standard gamepad buttons
                    btn_gamepad = any(k in (
                        evdev.ecodes.BTN_GAMEPAD,
                        evdev.ecodes.BTN_SOUTH,
                        evdev.ecodes.BTN_A,
                        evdev.ecodes.BTN_JOYSTICK
                    ) for k in key_codes) if has_keys else False

                    # Check for tablet pad buttons (BTN_0..BTN_9, BTN_STYLUS)
                    btn_tablet = any(k in (
                        evdev.ecodes.BTN_STYLUS,
                        evdev.ecodes.BTN_STYLUS2,
                        evdev.ecodes.BTN_TOOL_PEN,
                        evdev.ecodes.BTN_0
                    ) for k in key_codes) if has_keys else False

                    is_tablet = bool(
                        TABLET_PATTERNS.search(dev.name) or
                        dev.info.vendor in KNOWN_TABLET_VENDORS or
                        (btn_tablet and not btn_gamepad)
                    )

                    is_gamepad = bool(
                        btn_gamepad and not is_tablet
                    )

                    # Look for associated jsX node
                    js_node = None
                    try:
                        ev_num = Path(path).name.replace("event", "")
                        sys_input = Path(f"/sys/class/input/event{ev_num}/device")
                        if sys_input.exists():
                            for child in sys_input.iterdir():
                                if child.name.startswith("js"):
                                    js_node = child.name
                                    break
                    except Exception:
                        pass

                    devices.append({
                        "path": dev.path,
                        "name": dev.name,
                        "phys": dev.phys,
                        "vendor_id": f"0x{dev.info.vendor:04x}",
                        "product_id": f"0x{dev.info.product:04x}",
                        "is_gamepad": is_gamepad,
                        "is_tablet": is_tablet,
                        "js_node": js_node,
                    })
                except Exception:
                    continue
        except Exception:
            pass

    return devices

def get_status():
    devs = scan_devices()
    gamepads = [d for d in devs if d["is_gamepad"]]
    tablets = [d for d in devs if d["is_tablet"] and d.get("js_node")]

    primary = gamepads[0] if gamepads else None
    tablet_conflict = any(t.get("js_node") in ("js0", "js1", "js2") for t in tablets)

    return {
        "connected": bool(primary),
        "primary_name": primary["name"] if primary else "No controller connected",
        "primary_node": primary["path"] if primary else None,
        "primary_js": primary["js_node"] if primary else None,
        "tablet_conflict": tablet_conflict,
        "conflict_tablets": [t["name"] for t in tablets],
        "gamepad_count": len(gamepads),
        "gamepads": gamepads
    }

def print_list():
    status = get_status()
    print("======================================================================")
    print("  🎮 OMARCHY CONTROLLER STEWARD — INPUT DEVICE AUDIT")
    print("======================================================================")
    if status["connected"]:
        print(f"  • Primary Controller: {status['primary_name']}")
        print(f"    - Event Node:       {status['primary_node']}")
        print(f"    - Joystick Slot:    {status['primary_js'] or 'Not assigned'}")
    else:
        print("  • Primary Controller: None detected")

    if status["tablet_conflict"]:
        print("\n  ⚠️  TABLET INTERFERENCE DETECTED:")
        print("      Drawing tablet monitors/pads have claimed early joystick slots (js0-js2).")
        for t in status["conflict_tablets"]:
            print(f"      - {t}")
        print("      Run 'omarchy-games controller fix' to isolate drawing tablets from games.")
    else:
        print("\n  ✓ No joystick slot conflicts detected.")

    print("\n  ALL DETECTED CONTROLLERS:")
    for i, gp in enumerate(status["gamepads"]):
        print(f"    [{i}] {gp['name']} ({gp['vendor_id']}:{gp['product_id']}) -> {gp['js_node'] or gp['path']}")
    print("======================================================================")

def apply_fix():
    print("🔧 Applying Omarchy Controller & Tablet Isolation Fix...")
    env_dir = Path.home() / ".config" / "environment.d"
    env_dir.mkdir(parents=True, exist_ok=True)
    env_file = env_dir / "60-omarchy-gamepad.conf"

    # Known tablet devices to ignore in SDL
    content = (
        "# Omarchy Gamepad Steward\n"
        "# Automatically generated to keep drawing tablet pads from interfering with gamepads\n"
        "SDL_GAMECONTROLLER_IGNORE_DEVICES=0x256c/0x006d,0x056a/0x037a,0x28bd/0x0042\n"
    )

    with open(env_file, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✓ Written SDL tablet isolation overrides to {env_file}")

    # Create local udev rule template
    udev_rule_content = (
        "# Omarchy Gamepad Steward - Huion/Drawing Tablet Joystick Removal\n"
        "# Disables ID_INPUT_JOYSTICK on tablet button pads so real controllers take js0\n"
        'SUBSYSTEM=="input", ATTRS{idVendor}=="256c", ATTRS{idProduct}=="006d", ENV{ID_INPUT_TABLET_PAD}=="1", ENV{ID_INPUT_JOYSTICK}=""\n'
        'SUBSYSTEM=="input", ATTRS{idVendor}=="256c", ATTRS{idProduct}=="006d", ENV{ID_INPUT_TABLET}=="1", ENV{ID_INPUT_JOYSTICK}=""\n'
    )

    udev_target = Path("/etc/udev/rules.d/99-omarchy-tablet-no-joystick.rules")
    if not udev_target.exists():
        tmp_rule = Path.home() / ".config" / "omarchy" / "games" / "99-omarchy-tablet-no-joystick.rules"
        tmp_rule.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_rule, "w", encoding="utf-8") as f:
            f.write(udev_rule_content)
        print(f"  ℹ️  To permanently remove tablet js0-js2 at kernel level, run:")
        print(f"      sudo cp {tmp_rule} /etc/udev/rules.d/ && sudo udevadm control --reload-rules && sudo udevadm trigger")
    else:
        print("  ✓ System udev rule already active at /etc/udev/rules.d/99-omarchy-tablet-no-joystick.rules")

    print("\n✓ Controller steward configuration updated!")

def live_test():
    evdev = get_evdev()
    if evdev is None:
        print("Error: python-evdev is required for live testing.", file=sys.stderr)
        sys.exit(1)

    status = get_status()
    if not status["connected"]:
        print("❌ No controller connected to test.", file=sys.stderr)
        sys.exit(1)

    node = status["primary_node"]
    name = status["primary_name"]
    print(f"🎮 Testing {name} on {node} (Press Ctrl+C to exit)...")
    print("Press buttons, move analog sticks, or pull triggers:\n")

    try:
        dev = evdev.InputDevice(node)
        for event in dev.read_loop():
            if event.type == evdev.ecodes.EV_KEY:
                key_name = evdev.ecodes.BTN.get(event.code, str(event.code))
                action = "PRESSED" if event.value == 1 else "RELEASED"
                print(f"\r  [BUTTON] {key_name:<20} -> {action:<10}", end="", flush=True)
            elif event.type == evdev.ecodes.EV_ABS:
                axis_name = evdev.ecodes.ABS.get(event.code, str(event.code))
                print(f"\r  [AXIS]   {axis_name:<20} -> {event.value:<10}", end="", flush=True)
    except KeyboardInterrupt:
        print("\n\n✓ Test completed.")

def main():
    parser = argparse.ArgumentParser(description="Omarchy Controller Steward")
    parser.add_argument("command", choices=["list", "status", "fix", "test", "json"], nargs="?", default="list")
    args = parser.parse_args()

    if args.command == "list":
        print_list()
    elif args.command == "status":
        st = get_status()
        print(f"{st['primary_name']} ({'Slot ' + st['primary_js'] if st['primary_js'] else 'Active'})")
    elif args.command == "json":
        print(json.dumps(get_status(), indent=2))
    elif args.command == "fix":
        apply_fix()
    elif args.command == "test":
        live_test()

if __name__ == "__main__":
    main()
