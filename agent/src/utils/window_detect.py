# agent/src/utils/window_detect.py
"""Win32 active window title detection. Windows-only."""
import ctypes
import ctypes.wintypes


def get_active_window_title() -> str:
    """Return the title bar text of the currently focused window."""
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value
