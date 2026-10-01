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

                    # Look for associated jsX node in /dev/input
                    js_node = None
                    try:
                        ev_num = Path(path).name.replace("event", "")
                        sys_input = Path(f"/sys/class/input/event{ev_num}/device")
                        if sys_input.exists():
                            for child in sys_input.iterdir():
                                if child.name.startswith("js"):
                                    dev_file = Path(f"/dev/input/{child.name}")
                                    if dev_file.exists() and os.access(dev_file, os.R_OK):
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

def is_tablet_isolated():
    env_file = Path.home() / ".config" / "environment.d" / "60-omarchy-gamepad.conf"
    sdl_isolated = False
    if env_file.exists():
        try:
            content = env_file.read_text(encoding="utf-8")
            if "SDL_GAMECONTROLLER_IGNORE_DEVICES" in content and "256c" in content:
                sdl_isolated = True
        except Exception:
            pass

    udev_file = Path("/etc/udev/rules.d/99-omarchy-tablet-no-joystick.rules")
    udev_active = udev_file.exists()
    return sdl_isolated, udev_active

def get_status():
    devs = scan_devices()
    gamepads = [d for d in devs if d["is_gamepad"]]
    tablets = [d for d in devs if d["is_tablet"] and d.get("js_node")]

    primary = gamepads[0] if gamepads else None
    sdl_isolated, udev_active = is_tablet_isolated()

    has_active_tablet_js = any(t.get("js_node") in ("js0", "js1", "js2") for t in tablets)
    tablet_conflict = has_active_tablet_js and not udev_active

    return {
        "connected": bool(primary),
        "primary_name": primary["name"] if primary else "No controller connected",
        "primary_node": primary["path"] if primary else None,
        "primary_js": primary["js_node"] if primary else None,
        "tablet_conflict": tablet_conflict,
        "tablet_isolated": bool(sdl_isolated or udev_active),
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
    elif status["tablet_isolated"]:
        print("\n  ✓ Drawing tablets isolated (SDL / udev rules active).")
    else:
        print("\n  ✓ No joystick slot conflicts detected.")

    print("\n  ALL DETECTED CONTROLLERS:")
    for i, gp in enumerate(status["gamepads"]):
        print(f"    [{i}] {gp['name']} ({gp['vendor_id']}:{gp['product_id']}) -> {gp['js_node'] or gp['path']}")
    print("======================================================================")

def apply_fix():
    print("======================================================================")
    print("  🎮 OMARCHY CONTROLLER STEWARD — TABLET ISOLATION FIX")
    print("======================================================================")
    print("\n[1/3] Configuring SDL gamepad isolation...")
    env_dir = Path.home() / ".config" / "environment.d"
    env_dir.mkdir(parents=True, exist_ok=True)
    env_file = env_dir / "60-omarchy-gamepad.conf"

    content = (
        "# Omarchy Gamepad Steward\n"
        "# Automatically generated to keep drawing tablet pads from interfering with gamepads\n"
        "SDL_GAMECONTROLLER_IGNORE_DEVICES=0x256c/0x006d,0x056a/0x037a,0x28bd/0x0042\n"
    )
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✓ Written SDL tablet isolation overrides to {env_file}")

    print("\n[2/3] Installing system udev rule for drawing tablet isolation...")
    udev_rule_content = (
        "# Omarchy Gamepad Steward - Huion & Drawing Tablet Joystick Neutralizer\n"
        "# Prevents drawing tablets from taking joystick slots (js0-js2) away from real controllers.\n"
        "\n"
        "# Huion\n"
        'SUBSYSTEM=="input", ATTRS{idVendor}=="256c", KERNEL=="js[0-9]*", MODE="0000", ENV{ID_INPUT_JOYSTICK}="", RUN+="/usr/bin/rm -f /dev/input/%k"\n'
        'SUBSYSTEM=="input", ATTRS{idVendor}=="256c", ENV{ID_INPUT_JOYSTICK}=="?*", ENV{ID_INPUT_JOYSTICK}=""\n'
        "\n"
        "# Wacom\n"
        'SUBSYSTEM=="input", ATTRS{idVendor}=="056a", KERNEL=="js[0-9]*", MODE="0000", ENV{ID_INPUT_JOYSTICK}="", RUN+="/usr/bin/rm -f /dev/input/%k"\n'
        'SUBSYSTEM=="input", ATTRS{idVendor}=="056a", ENV{ID_INPUT_JOYSTICK}=="?*", ENV{ID_INPUT_JOYSTICK}=""\n'
        "\n"
        "# XP-Pen\n"
        'SUBSYSTEM=="input", ATTRS{idVendor}=="28bd", KERNEL=="js[0-9]*", MODE="0000", ENV{ID_INPUT_JOYSTICK}="", RUN+="/usr/bin/rm -f /dev/input/%k"\n'
        'SUBSYSTEM=="input", ATTRS{idVendor}=="28bd", ENV{ID_INPUT_JOYSTICK}=="?*", ENV{ID_INPUT_JOYSTICK}=""\n'
    )

    staging = Path.home() / ".config" / "omarchy" / "games" / "99-omarchy-tablet-no-joystick.rules"
    staging.parent.mkdir(parents=True, exist_ok=True)
    staging.write_text(udev_rule_content, encoding="utf-8")

    import subprocess

    udev_target = Path("/etc/udev/rules.d/99-omarchy-tablet-no-joystick.rules")
    if os.geteuid() == 0:
        udev_target.write_text(udev_rule_content, encoding="utf-8")
        subprocess.run(["udevadm", "control", "--reload-rules"], check=False)
        for js in Path("/dev/input").glob("js*"):
            try:
                out = subprocess.check_output(["udevadm", "info", str(js)], text=True, errors="replace")
                if any(v in out for v in ["ID_VENDOR_ID=256c", "ID_VENDOR_ID=056a", "ID_VENDOR_ID=28bd"]):
                    js.unlink(missing_ok=True)
            except Exception:
                pass
        print("  ✓ System udev rule installed directly and rules reloaded.")
    else:
        print("  [Requesting administrator privilege via sudo to install udev rule]")
        cmd = (
            f"cp '{staging}' /etc/udev/rules.d/99-omarchy-tablet-no-joystick.rules && "
            "udevadm control --reload-rules && "

            "for js in /dev/input/js[0-9]*; do [ -e \"$js\" ] || continue; "
            "udevadm info \"$js\" 2>/dev/null | grep -Eq 'ID_VENDOR_ID=(256c|056a|28bd)' && rm -f \"$js\" || true; done"
        )
        try:
            res = subprocess.run(["sudo", "sh", "-c", cmd])
            if res.returncode == 0:
                print("  ✓ System udev rule installed and tablet joystick nodes neutralized.")
            else:
                print("  ⚠️ Sudo elevation failed or was cancelled.", file=sys.stderr)
        except Exception as e:
            print(f"  ⚠️ Error running sudo: {e}", file=sys.stderr)

    print("\n[3/3] Verifying status...")
    st = get_status()
    if not st["tablet_conflict"]:
        print("  ✓ All tablet joystick conflicts successfully resolved!")
        if st["connected"]:
            print(f"  ✓ Active Gamepad: {st['primary_name']} ({st['primary_js'] or st['primary_node']})")
    else:
        print("  ⚠️ Some tablet nodes may still be active. Replugging your controller or a reboot may be needed.")

    print("\n======================================================================")
    print("  Fix completed!")
    print("======================================================================")
    if sys.stdout.isatty():
        try:
            input("\nPress Enter to close...")
        except Exception:
            pass

def live_test():
    evdev = get_evdev()
    if evdev is None:
        print("❌ Error: python-evdev is required for live testing.", file=sys.stderr)
        if sys.stdout.isatty():
            input("\nPress Enter to exit...")
        sys.exit(1)

    status = get_status()
    if not status["connected"]:
        print("❌ No controller connected to test.", file=sys.stderr)
        if sys.stdout.isatty():
            input("\nPress Enter to exit...")
        sys.exit(1)

    node = status["primary_node"]
    name = status["primary_name"]
    js = status.get("primary_js")

    print("======================================================================")
    print("  🎮 OMARCHY CONTROLLER INPUT TESTER")
    print("======================================================================")
    print(f"  Device: {name}")
    print(f"  Node:   {node} ({js or 'No js slot'})")
    print("----------------------------------------------------------------------")
    print("  Press buttons, move sticks, or pull triggers.")
    print("  Press Ctrl+C to stop testing.\n")

    try:
        dev = evdev.InputDevice(node)
        for event in dev.read_loop():
            if event.type == evdev.ecodes.EV_KEY:
                raw_name = evdev.ecodes.BTN.get(event.code, str(event.code))
                if isinstance(raw_name, (list, tuple)):
                    key_name = raw_name[0]
                else:
                    key_name = str(raw_name)
                action = "PRESSED " if event.value == 1 else "RELEASED"
                print(f"\r  [BUTTON] {key_name:<24} -> {action:<10}", end="", flush=True)
            elif event.type == evdev.ecodes.EV_ABS:
                axis_name = evdev.ecodes.ABS.get(event.code, str(event.code))
                print(f"\r  [AXIS]   {axis_name:<24} -> {event.value:<10}", end="", flush=True)
    except KeyboardInterrupt:
        print("\n\n✓ Input test completed.")
        time.sleep(0.5)
    except Exception as e:
        print(f"\n❌ Error reading controller events: {e}", file=sys.stderr)
        if sys.stdout.isatty():
            input("\nPress Enter to exit...")

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
