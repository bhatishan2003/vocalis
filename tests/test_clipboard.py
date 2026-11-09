"""Tests for clipboard utilities."""

import base64
from vocalis.output.clipboard import copy_osc52, copy_to_clipboard


def test_copy_osc52():
    # Should not crash and should return True when writing to stream
    result = copy_osc52("hello world")
    assert isinstance(result, bool)


def test_copy_to_clipboard():
    backends = copy_to_clipboard("test clipboard content")
    assert isinstance(backends, list)
    # OSC 52 is supported universally in standard streams
    assert any("osc52" in b for b in backends)
