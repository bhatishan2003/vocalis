"""Universal clipboard integration supporting OSC 52, Wayland, and X11."""

from __future__ import annotations

import base64
import os
import shutil
import subprocess
import sys


def copy_osc52(text: str) -> bool:
    """Copy text to clipboard using ANSI OSC 52 escape sequences.

    This works inside VS Code, Cursor, Neovim terminal, tmux, WezTerm,
    Alacritty, Kitty, and modern terminal emulators across local and remote sessions.
    """
    try:
        encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
        osc = f"\033]52;c;{encoded}\a"

        # Try writing directly to the controlling terminal (/dev/tty)
        try:
            with open("/dev/tty", "w") as tty:
                tty.write(osc)
                tty.flush()
                return True
        except (OSError, PermissionError):
            pass

        # Fallback to sys.stderr or sys.stdout
        sys.stderr.write(osc)
        sys.stderr.flush()
        return True
    except Exception:
        return False


def copy_native(text: str) -> bool:
    """Copy text using native desktop clipboard utilities (wl-copy, xclip, xsel)."""
    # 1. Wayland
    if shutil.which("wl-copy"):
        try:
            proc = subprocess.run(
                ["wl-copy"],
                input=text.encode("utf-8"),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if proc.returncode == 0:
                return True
        except Exception:
            pass

    # 2. X11 xclip
    if shutil.which("xclip"):
        try:
            proc = subprocess.run(
                ["xclip", "-selection", "clipboard"],
                input=text.encode("utf-8"),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if proc.returncode == 0:
                return True
        except Exception:
            pass

    # 3. X11 xsel
    if shutil.which("xsel"):
        try:
            proc = subprocess.run(
                ["xsel", "--clipboard", "--input"],
                input=text.encode("utf-8"),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if proc.returncode == 0:
                return True
        except Exception:
            pass

    return False


def copy_to_clipboard(text: str) -> list[str]:
    """Copy text to clipboard using all available channels.

    Returns:
        List of successful backends (e.g. ['osc52', 'wl-copy'])
    """
    backends_used: list[str] = []

    # Try native tool first if available
    if copy_native(text):
        backends_used.append("desktop-clipboard")

    # Always trigger OSC 52 because it copies directly to the editor host
    if copy_osc52(text):
        backends_used.append("terminal-osc52")

    return backends_used
