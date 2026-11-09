"""Tests for audio conversion and WAV generation."""

import io
import numpy as np
from scipy.io import wavfile
from vocalis.audio.recorder import AudioRecorder


def test_to_mono():
    # 1D array
    arr_1d = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    assert np.array_equal(AudioRecorder.to_mono(arr_1d), arr_1d)

    # 2D stereo array
    arr_stereo = np.array([[0.2, 0.4], [0.6, 0.8]], dtype=np.float32)
    mono = AudioRecorder.to_mono(arr_stereo)
    assert np.allclose(mono, np.array([0.3, 0.7], dtype=np.float32))


def test_to_wav_bytes():
    sample_rate = 16000
    # 0.5s of 440Hz tone
    t = np.linspace(0, 0.5, int(sample_rate * 0.5), endpoint=False)
    signal = 0.5 * np.sin(2 * np.pi * 440 * t)

    wav_bytes = AudioRecorder.to_wav_bytes(signal, sample_rate=sample_rate)
    assert len(wav_bytes) > 0

    # Read back with scipy to verify it is a valid 16kHz WAV
    buf = io.BytesIO(wav_bytes)
    sr, data = wavfile.read(buf)
    assert sr == sample_rate
    assert data.dtype == np.int16
    assert len(data) == len(signal)
