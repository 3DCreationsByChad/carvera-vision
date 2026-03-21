"""
Window detection and screenshot utilities for carvera-vision.

Handles finding the MakeraCam window across platforms and capturing it
as a base64-encoded PNG suitable for passing to Claude.
"""

from __future__ import annotations

import base64
import io
import platform
import subprocess
from dataclasses import dataclass
from typing import Optional

from PIL import Image

# Window title substrings to search for (case-insensitive).
# IMPORTANT: keep these specific. Short substrings like "carvera" match browser
# tabs (e.g. a Chrome tab open to github.com/…/carvera-vision). Use the longest
# reliable prefix of the actual desktop app title to avoid false matches.
MAKERA_WINDOW_ALIASES = [
    "makeracam",      # MakeraCam standalone desktop app
    "makera cam",     # alternate spacing variant
    "carvera air",    # Carvera Air desktop software title prefix
    "makera",         # fallback: matches "Makera" app window but not "carvera-vision" browser tabs
]

# Browser/web process identifiers to skip even if an alias matches.
# Guards against future false matches on browser tabs.
_BROWSER_SKIP_SUBSTRINGS = [
    "chrome",
    "firefox",
    "edge",
    "brave",
    "browser",
    "github.com",
]

SYSTEM = platform.system()  # "Windows", "Darwin", "Linux"


@dataclass
class WindowInfo:
    title: str
    left: int
    top: int
    width: int
    height: int


def find_makera_window() -> Optional[WindowInfo]:
    """
    Search running windows for a MakeraCam/Carvera window.
    Returns the first match as a WindowInfo, or None if not found.
    """
    if SYSTEM == "Windows":
        return _find_window_windows()
    elif SYSTEM == "Darwin":
        return _find_window_macos()
    else:
        return _find_window_linux()


def capture_window(window: WindowInfo, scale: float = 1.0) -> tuple[str, int, int]:
    """
    Capture a specific window region and return (base64_png, width, height).

    Args:
        window: WindowInfo describing the region to capture.
        scale: Downscale factor (0.5 = half size). Useful for large 4K displays
               to keep token count reasonable without losing readability.
    """
    import mss

    with mss.mss() as sct:
        region = {
            "left": window.left,
            "top": window.top,
            "width": window.width,
            "height": window.height,
        }
        raw = sct.grab(region)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

    if scale != 1.0:
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return b64, img.width, img.height


def list_all_windows() -> list[str]:
    """Return a list of all visible window titles on the system."""
    if SYSTEM == "Windows":
        return _list_windows_windows()
    elif SYSTEM == "Darwin":
        return _list_windows_macos()
    else:
        return _list_windows_linux()


# ── Windows ───────────────────────────────────────────────────────────────────

def _find_window_windows() -> Optional[WindowInfo]:
    try:
        import pygetwindow as gw
        windows = gw.getAllWindows()
        for w in windows:
            if not w.title:
                continue
            title_lower = w.title.lower()
            if any(alias in title_lower for alias in MAKERA_WINDOW_ALIASES):
                if any(skip in title_lower for skip in _BROWSER_SKIP_SUBSTRINGS):
                    continue
                # pygetwindow can return negative coords if window is off-screen
                left = max(0, w.left)
                top = max(0, w.top)
                return WindowInfo(
                    title=w.title,
                    left=left,
                    top=top,
                    width=w.width,
                    height=w.height,
                )
    except Exception:
        pass
    return None


def _list_windows_windows() -> list[str]:
    try:
        import pygetwindow as gw
        return [w.title for w in gw.getAllWindows() if w.title.strip()]
    except Exception:
        return []


# ── macOS ─────────────────────────────────────────────────────────────────────

def _find_window_macos() -> Optional[WindowInfo]:
    """Use AppleScript to find and get geometry of the MakeraCam window."""
    script = """
    tell application "System Events"
        set winList to {}
        repeat with proc in (every process whose background only is false)
            repeat with win in (every window of proc)
                set winList to winList & {{name of proc, name of win, position of win, size of win}}
            end repeat
        end repeat
        return winList
    end tell
    """
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=5
        )
        lines = result.stdout.strip().split(", ")
        # Parse the flat list: app, title, x, y, w, h repeating
        i = 0
        while i + 5 < len(lines):
            title = lines[i + 1].strip()
            title_lower = title.lower()
            if any(alias in title_lower for alias in MAKERA_WINDOW_ALIASES):
                if not any(skip in title_lower for skip in _BROWSER_SKIP_SUBSTRINGS):
                    try:
                        x = int(lines[i + 2])
                        y = int(lines[i + 3])
                        w = int(lines[i + 4])
                        h = int(lines[i + 5])
                        return WindowInfo(title=title, left=x, top=y, width=w, height=h)
                    except ValueError:
                        pass
            i += 6
    except Exception:
        pass
    return None


def _list_windows_macos() -> list[str]:
    script = """
    tell application "System Events"
        set names to {}
        repeat with proc in (every process whose background only is false)
            repeat with win in (every window of proc)
                set names to names & {name of win}
            end repeat
        end repeat
        return names
    end tell
    """
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=5
        )
        return [t.strip() for t in result.stdout.split(",") if t.strip()]
    except Exception:
        return []


# ── Linux ─────────────────────────────────────────────────────────────────────

def _find_window_linux() -> Optional[WindowInfo]:
    """Use wmctrl to find the window geometry on Linux."""
    try:
        result = subprocess.run(
            ["wmctrl", "-lG"], capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            parts = line.split(None, 8)
            if len(parts) < 9:
                continue
            title = parts[8]
            title_lower = title.lower()
            if any(alias in title_lower for alias in MAKERA_WINDOW_ALIASES):
                if any(skip in title_lower for skip in _BROWSER_SKIP_SUBSTRINGS):
                    continue
                x, y, w, h = int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
                return WindowInfo(title=title, left=x, top=y, width=w, height=h)
    except FileNotFoundError:
        pass  # wmctrl not installed
    except Exception:
        pass
    return None


def _list_windows_linux() -> list[str]:
    try:
        result = subprocess.run(
            ["wmctrl", "-l"], capture_output=True, text=True, timeout=5
        )
        titles = []
        for line in result.stdout.splitlines():
            parts = line.split(None, 3)
            if len(parts) == 4:
                titles.append(parts[3].strip())
        return titles
    except Exception:
        return []
