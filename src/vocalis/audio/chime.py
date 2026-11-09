"""Non-blocking audio cues and earcons for Vocalis."""

from __future__ import annotations

import io
import shutil
import subprocess
import threading
from typing import Optional

import numpy as np
from scipy.io import wavfile


class ChimePlayer:
    """Generates and plays lightweight audio chimes for voice state transitions."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._start_wav: Optional[bytes] = None
        self._done_wav: Optional[bytes] = None
        if self.enabled:
            self._prepare_chimes()

    def _generate_tone(self, freq: float, duration: float, volume: float = 0.12) -> bytes:
        """Synthesize a soft sine wave chime with smooth cosine envelope."""
        sample_rate = 16000
        num_samples = int(sample_rate * duration)
        t = np.linspace(0, duration, num_samples, endpoint=False)

        # Smooth bell envelope (raised cosine) to eliminate clicks
        envelope = np.sin(np.pi * t / duration)
        signal = (envelope * volume * np.sin(2 * np.pi * freq * t) * 32767.0).astype(np.int16)

        buf = io.BytesIO()
        wavfile.write(buf, sample_rate, signal)
        return buf.getvalue()

    def _prepare_chimes(self) -> None:
        """Pre-generate in-memory WAV bytes so playback has zero computational latency."""
        try:
            # Start chime: Pleasant high A5 (880 Hz, 35ms)
            self._start_wav = self._generate_tone(880.0, 0.035, volume=0.10)
            # Done chime: Bright C6 (1046.5 Hz, 45ms)
            self._done_wav = self._generate_tone(1046.5, 0.045, volume=0.10)
        except Exception:
            self.enabled = False

    def _play_raw(self, wav_bytes: Optional[bytes]) -> None:
        """Play WAV audio in a subprocess without blocking the main thread."""
        if not self.enabled or not wav_bytes:
            return

        def worker():
            for cmd in (["aplay", "-q"], ["pw-play", "-"]):
                if shutil.which(cmd[0]):
                    try:
                        proc = subprocess.Popen(
                            cmd,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        proc.communicate(input=wav_bytes, timeout=0.6)
                        return
                    except Exception:
                        continue

        threading.Thread(target=worker, daemon=True).start()

    def play_start(self) -> None:
        """Play cue when speech starts."""
        self._play_raw(self._start_wav)

    def play_done(self) -> None:
        """Play cue when processing completes and text is typed."""
        self._play_raw(self._done_wav)
