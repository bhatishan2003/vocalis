"""Tests for Voice Activity Detection and energy analysis."""

import numpy as np
import pytest
from vocalis.audio.vad import SpeechState, VADDetector


def test_calculate_rms():
    # Silence
    silence = np.zeros(1600, dtype=np.float32)
    assert VADDetector.calculate_rms(silence) == 0.0

    # Sine wave with amplitude 0.5 -> RMS = 0.5 / sqrt(2) ~ 0.3535
    t = np.linspace(0, 0.1, 1600, endpoint=False)
    sine = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    rms = VADDetector.calculate_rms(sine)
    assert pytest.approx(rms, rel=1e-2) == 0.3535

    # Multi-channel
    stereo = np.column_stack([sine, sine])
    rms_stereo = VADDetector.calculate_rms(stereo)
    assert pytest.approx(rms_stereo, rel=1e-2) == 0.3535


def test_vad_state_transitions():
    vad = VADDetector(
        sample_rate=16000,
        energy_threshold=0.02,
        silence_duration=0.2,  # fast timeout for test
        min_record_seconds=0.1,
    )

    silence_chunk = np.zeros(1600, dtype=np.float32)
    loud_chunk = np.ones(1600, dtype=np.float32) * 0.1

    # Calibrate ambient noise (first 4 chunks)
    for _ in range(4):
        state, _ = vad.process_chunk(silence_chunk)
        assert state == SpeechState.IDLE

    # Still idle during silence
    state, _ = vad.process_chunk(silence_chunk)
    assert state == SpeechState.IDLE

    # Speech starts
    state, rms = vad.process_chunk(loud_chunk)
    assert state == SpeechState.SPEAKING
    assert rms > 0.05

    # Continue speaking
    state, _ = vad.process_chunk(loud_chunk)
    assert state == SpeechState.SPEAKING

    # Speech pauses
    state, _ = vad.process_chunk(silence_chunk)
    assert state == SpeechState.PAUSED
