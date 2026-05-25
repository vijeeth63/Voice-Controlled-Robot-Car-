#!/usr/bin/env python3
"""
Keyboard → HTTP controller for an ESP32 bot on the same LAN.

ESP32 routes:
  GET /F, /B, /L, /R, /S     — forward, backward, left, right, stop
  GET /SPD/LOW, /SPD/MED, /SPD/HIGH — speed control
"""

import argparse
import sys
import threading
import time

import requests
from pynput import keyboard as kb

DEFAULT_ESP_URL = "http://192.168.1.192"


def build_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"Connection": "keep-alive"})
    return s


def send_command(session: requests.Session, base_url: str, endpoint: str) -> None:
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    try:
        response = session.get(url, timeout=(1.0, 2.0))
        print(f"[{endpoint}] {response.text}")
    except requests.exceptions.ReadTimeout:
        print(f"[{endpoint}] Command sent (ESP32 slow to respond)")
    except requests.exceptions.RequestException as e:
        print(f"[{endpoint}] Connection failed: {e}")


def test_reachability(session: requests.Session, base_url: str) -> bool:
    url = f"{base_url.rstrip('/')}/S"
    try:
        r = session.get(url, timeout=(2.0, 3.0))
        print(f"Reachability OK — HTTP {r.status_code}, body: {r.text!r}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Reachability FAILED: {e}")
        return False


def _char_from_key(key: kb.Key | kb.KeyCode | None) -> str | None:
    if key is None:
        return None
    # Handle digit keys (KeyCode with char '1', '2', '3')
    try:
        ch = getattr(key, "char", None)
    except AttributeError:
        return None
    if ch is None:
        return None
    if ch.isalpha():
        return ch.lower()
    if ch in ('1', '2', '3'):
        return ch
    return None


def run_controller(base_url: str) -> None:
    session = build_session()
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

    print("=== ESP32 Bot Controller ===")
    print(f"Target: {base_url}")
    print("Move  : W Forward | S Back | A Left | D Right | E Stop")
    print("Speed : 1 Low     | 2 Med  | 3 High")
    print("Quit  : Q (sends stop first)")
    print("(macOS: grant Accessibility to this terminal app)\n")

    last_cmd = None
    current_speed = "MED"

    try:
        while True:
            # Speed keys — checked first, independent of direction
            if is_down('1'):
                if current_speed != "LOW":
                    send_command(session, base_url, "SPD/LOW")
                    current_speed = "LOW"
                    print(">> Speed: LOW")
                    time.sleep(0.2)

            elif is_down('2'):
                if current_speed != "MED":
                    send_command(session, base_url, "SPD/MED")
                    current_speed = "MED"
                    print(">> Speed: MED")
                    time.sleep(0.2)

            elif is_down('3'):
                if current_speed != "HIGH":
                    send_command(session, base_url, "SPD/HIGH")
                    current_speed = "HIGH"
                    print(">> Speed: HIGH")
                    time.sleep(0.2)

            # Direction keys
            elif is_down('w'):
                if last_cmd != 'F':
                    send_command(session, base_url, "F")
                    last_cmd = 'F'

            elif is_down('s'):
                if last_cmd != 'B':
                    send_command(session, base_url, "B")
                    last_cmd = 'B'

            elif is_down('a'):
                if last_cmd != 'L':
                    send_command(session, base_url, "L")
                    last_cmd = 'L'

            elif is_down('d'):
                if last_cmd != 'R':
                    send_command(session, base_url, "R")
                    last_cmd = 'R'

            elif is_down('e'):
                if last_cmd != 'S':
                    send_command(session, base_url, "S")
                    last_cmd = 'S'

            elif is_down('q'):
                print("Exiting…")
                send_command(session, base_url, "S")
                break

            else:
                last_cmd = None

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nInterrupted. Sending stop.")
        send_command(session, base_url, "S")
    finally:
        listener.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Control ESP32 bot over HTTP from the keyboard.")
    parser.add_argument(
        "--url",
        default=DEFAULT_ESP_URL,
        help=f"Base URL of the ESP32 (default: {DEFAULT_ESP_URL})",
    )
    parser.add_argument(
        "--test", 
        action="store_true",
        help="Only check HTTP reachability, then exit.",
    )
    args = parser.parse_args()
    base = args.url.strip()
    if not base.lower().startswith("http"):
        print("Error: --url must start with http:// or https://", file=sys.stderr)
        sys.exit(1)

    session = build_session()
    if args.test:
        ok = test_reachability(session, base)
        sys.exit(0 if ok else 1)

    run_controller(base)


if __name__ == "__main__":
    main()
