"""Tests for TextInjector."""

from unittest.mock import MagicMock
from vocalis.output.injector import TextInjector


def test_injector_methods(monkeypatch):
    injector = TextInjector()
    if injector.is_available:
        mock_keyboard = MagicMock()
        injector.keyboard = mock_keyboard

        # Type text
        success = injector.type_text("hello", char_delay=0)
        assert success is True
        mock_keyboard.type.assert_called_with("hello")

        # Inject with space
        success = injector.inject("testing", method="type", append_space=True, char_delay=0)
        assert success is True
        mock_keyboard.type.assert_called_with("testing ")
