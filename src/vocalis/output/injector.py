"""Direct text injection into active windows via simulated keystrokes."""

from __future__ import annotations

import time
from typing import Optional

try:
    from pynput.keyboard import Controller, Key
    PYNPUT_AVAILABLE = True
except Exception:
    PYNPUT_AVAILABLE = False


class TextInjector:
    """Injects transcribed text directly at the cursor in any focused window."""

    def __init__(self) -> None:
        self.keyboard = Controller() if PYNPUT_AVAILABLE else None

    @property
    def is_available(self) -> bool:
        """Check if keystroke injection is supported on this system."""
        return self.keyboard is not None

    def type_text(self, text: str, char_delay: float = 0.002) -> bool:
        """Type text character-by-character into the active cursor position.

        Args:
            text: String to type.
            char_delay: Seconds between keypresses to ensure smooth rendering.

        Returns:
            True if typing was executed, False otherwise.
        """
        if not self.is_available:
            return False

        try:
            if char_delay <= 0:
                self.keyboard.type(text)
            else:
                for char in text:
                    self.keyboard.type(char)
                    time.sleep(char_delay)
            return True
        except Exception:
            return False

    def paste_text(self, text: str) -> bool:
        """Simulate Ctrl+V to paste into active window."""
        if not self.is_available:
            return False

        try:
            with self.keyboard.pressed(Key.ctrl):
                self.keyboard.tap("v")
            return True
        except Exception:
            return False

    def inject(
        self,
        text: str,
        method: str = "type",
        append_space: bool = True,
        char_delay: float = 0.001,
    ) -> bool:
        """Inject text using the specified method (type or paste).

        Args:
            text: Text to insert.
            method: 'type' (direct character typing) or 'paste' (Ctrl+V).
            append_space: If True, adds a trailing space for continuous speaking.
            char_delay: Delay between characters if method == 'type'.
        """
        if not text:
            return False

        out_text = text
        if append_space and not out_text.endswith((" ", "\n", "\t")):
            out_text += " "

        if method == "paste":
            return self.paste_text(out_text)
        return self.type_text(out_text, char_delay=char_delay)
