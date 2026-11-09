"""Tests for audio chimes."""

from vocalis.audio.chime import ChimePlayer


def test_chime_generation():
    chimes = ChimePlayer(enabled=True)
    assert chimes.enabled is True
    assert chimes._start_wav is not None
    assert len(chimes._start_wav) > 100
    assert chimes._done_wav is not None
    assert len(chimes._done_wav) > 100


def test_chime_disabled():
    chimes = ChimePlayer(enabled=False)
    assert chimes.enabled is False
    assert chimes._start_wav is None
    # Should not crash
    chimes.play_start()
    chimes.play_done()
