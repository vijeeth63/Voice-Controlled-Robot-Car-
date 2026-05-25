#!/usr/bin/env python3
"""
Local keyboard → HTTP test client for the ESP32 bot.

Uses ``pynput`` (works on macOS with Accessibility enabled for Terminal/Cursor).
Install: ``pip install pynput requests``

Run:
  python3 keyboard_esp32_test.py
  python3 keyboard_esp32_test.py --ip http://192.168.1.192
"""

from __future__ import annotations

import argparse
import threading
import time

import requests
from pynput import keyboard as kb


def send_command(session: requests.Session, base_url: str, endpoint: str) -> None:
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    try:
        response = session.get(url, timeout=(1.0, 12.0))
        print(f"Command sent: {response.text!r}")
    except requests.exceptions.ReadTimeout:
        print(f"[{endpoint}] Command may have run; ESP32 response was slow.")
    except requests.exceptions.RequestException as e:
        print(f"Connection failed! Error: {e}")


def _char_from_key(key: kb.Key | kb.KeyCode | None) -> str | None:
    if key is None:
        return None
    try:
        ch = getattr(key, "char", None)
    except AttributeError:
        return None
    if ch is None:
        return None
    if ch.isalpha():
        return ch.lower()
    if ch in ("1", "2", "3"):
        return ch
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Keyboard control for ESP32 HTTP API.")
    parser.add_argument(
        "--ip",
        default="http://192.168.1.192",
        help="ESP32 base URL (default: http://192.168.1.192)",
    )
    args = parser.parse_args()
    base = args.ip.strip()

    session = requests.Session()
    session.headers.update({"Connection": "keep-alive"})

    pressed_lock = threading.Lock()
    pressed: set[str] = set()

    def on_press(key: kb.Key | kb.KeyCode | None) -> None:
        c = _char_from_key(key)
        if c:
            with pressed_lock:
                pressed.add(c)

    def on_release(key: kb.Key | kb.KeyCode | None) -> None:
        c = _char_from_key(key)
        if c:
            with pressed_lock:
                pressed.discard(c)

    listener = kb.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    def is_down(c: str) -> bool:
        with pressed_lock:
            return c in pressed

    print("=== ESP32 Bot Controller (keyboard test) ===")
    print(f"Target: {base}")
    print("Controls : W (Forward), S (Backward), A (Left), D (Right), E (Stop)")
    print("Speed    : 1 (Low), 2 (Medium), 3 (High)")
    print("Press 'Q' to quit.")
    print("Current speed: MEDIUM (default)")
    print("macOS: enable Accessibility for this terminal app.\n")
    print("Waiting for input...\n")

    last_command: str | None = None
    current_speed = "MED"

    try:
        while True:
            if is_down("1"):
                if current_speed != "LOW":
                    send_command(session, base, "SPD/LOW")
                    current_speed = "LOW"
                    print(">> Speed set to LOW")
                    time.sleep(0.2)

            elif is_down("2"):
                if current_speed != "MED":
                    send_command(session, base, "SPD/MED")
                    current_speed = "MED"
                    print(">> Speed set to MEDIUM")
                    time.sleep(0.2)

            elif is_down("3"):
                if current_speed != "HIGH":
                    send_command(session, base, "SPD/HIGH")
                    current_speed = "HIGH"
                    print(">> Speed set to HIGH")
                    time.sleep(0.2)

            elif is_down("w"):
                if last_command != "F":
                    send_command(session, base, "F")
                    last_command = "F"

            elif is_down("s"):
                if last_command != "B":
                    send_command(session, base, "B")
                    last_command = "B"

            elif is_down("a"):
                if last_command != "L":
                    send_command(session, base, "L")
                    last_command = "L"

            elif is_down("d"):
                if last_command != "R":
                    send_command(session, base, "R")
                    last_command = "R"

            elif is_down("e"):
                if last_command != "S":
                    send_command(session, base, "S")
                    last_command = "S"

            elif is_down("q"):
                print("Exiting controller...")
                send_command(session, base, "S")
                break

            else:
                last_command = None

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nProgram interrupted. Stopping car.")
        send_command(session, base, "S")
    finally:
        listener.stop()


if __name__ == "__main__":
    main()
