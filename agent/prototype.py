#!/usr/bin/env python3
"""
Smoke-test prototype — NOT production code.
Polls a fake in-memory endpoint; on Ctrl+Shift+A types 'Hello World' into
the active window. Run: cd agent && python prototype.py
"""

import threading
import time

import keyboard
import pyautogui

POLL_INTERVAL = 3
_pending: str | None = None
_lock = threading.Lock()


def _mock_poll() -> str | None:
    """Returns scan data every ~9 seconds (every 3rd poll)."""
    c = getattr(_mock_poll, "_c", 0) + 1
    _mock_poll._c = c
    return "Hello World" if c % 3 == 0 else None


def _poll_loop() -> None:
    global _pending
    print("[poller] started — will queue 'Hello World' every ~9s")
    while True:
        result = _mock_poll()
        with _lock:
            if result and _pending is None:
                _pending = result
                print("[poller] scan ready — press Ctrl+Shift+A")
        time.sleep(POLL_INTERVAL)


def _on_hotkey() -> None:
    global _pending
    with _lock:
        text, _pending = _pending, None
    if text is None:
        print("[hotkey] no scan pending")
        return
    print("[hotkey] typing into active window")
    time.sleep(0.15)
    pyautogui.typewrite(text, interval=0.05)
    print("[hotkey] done — data wiped from memory")


if __name__ == "__main__":
    pyautogui.FAILSAFE = True
    threading.Thread(target=_poll_loop, daemon=True).start()
    keyboard.add_hotkey("ctrl+shift+a", _on_hotkey)
    print("[main] Move mouse to corner to abort. Ctrl+Shift+A to type.")
    keyboard.wait()
