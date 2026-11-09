"""Audio recording using native system sound interfaces."""

from __future__ import annotations

import collections
import io
import sys
import threading
from typing import Callable, Optional

import numpy as np
from scipy.io import wavfile

# Guard against soundcard's sys.argv inspection in unusual environments
if not hasattr(sys, "argv") or len(sys.argv) < 2:
    if not hasattr(sys, "argv"):
        sys.argv = ["vocalis"]
    elif len(sys.argv) == 1 and sys.argv[0] == "-c":
        sys.argv.append("vocalis")

import soundcard as sc

from vocalis.audio.vad import SpeechState, VADDetector


class AudioRecorder:
    """Manages microphone input capture and voice activity listening."""

    def __init__(
        self,
        sample_rate: int = 16000,
        device_name: Optional[str] = None,
        block_size: int = 1600,  # 100ms at 16kHz
        silence_duration: float = 0.9,
        energy_threshold: float = 0.012,
    ) -> None:
        self.sample_rate = sample_rate
        self.device_name = device_name
        self.block_size = block_size
        self.silence_duration = silence_duration
        self.energy_threshold = energy_threshold

    @staticmethod
    def list_devices() -> list[str]:
        """List all available microphone device names."""
        try:
            mics = sc.all_microphones()
            return [m.name for m in mics]
        except Exception:
            return []

    def get_microphone(self) -> sc.Microphone:
        """Get the configured or default microphone."""
        if self.device_name:
            for mic in sc.all_microphones():
                if self.device_name.lower() in mic.name.lower():
                    return mic
        return sc.default_microphone()

    @staticmethod
    def to_mono(audio_chunk: np.ndarray) -> np.ndarray:
        """Convert multi-channel audio to mono 1D array."""
        if audio_chunk.ndim > 1:
            if audio_chunk.shape[1] > 1:
                return np.mean(audio_chunk, axis=1)
            return audio_chunk[:, 0]
        return audio_chunk

    @classmethod
    def to_wav_bytes(cls, audio_data: np.ndarray, sample_rate: int = 16000) -> bytes:
        """Convert float32/int16 numpy audio to in-memory WAV file bytes."""
        audio_mono = cls.to_mono(audio_data)

        # Normalize and convert float32 to 16-bit PCM for universal speech API compatibility
        if audio_mono.dtype != np.int16:
            # Clip between -1.0 and 1.0, scale to int16 range
            clipped = np.clip(audio_mono, -1.0, 1.0)
            pcm16 = (clipped * 32767.0).astype(np.int16)
        else:
            pcm16 = audio_mono

        buf = io.BytesIO()
        wavfile.write(buf, sample_rate, pcm16)
        return buf.getvalue()

    def record_utterance(
        self,
        on_chunk: Optional[Callable[[SpeechState, float, float], None]] = None,
        on_speech_started: Optional[Callable[[], None]] = None,
        stop_event: Optional[threading.Event] = None,
        manual_mode: bool = False,
    ) -> tuple[np.ndarray, float, bool]:
        """Record until speech ends (VAD) or stop_event is set.

        Args:
            on_chunk: Callback(state, rms, elapsed_sec) called every 100ms.
            on_speech_started: Callback called once when voice activity begins.
            stop_event: Threading event to externally signal stop.
            manual_mode: If True, only stop_event or timeout terminates recording.

        Returns:
            Tuple of (recorded_mono_numpy_array, duration_seconds, speech_started)
        """
        mic = self.get_microphone()
        vad = VADDetector(
            sample_rate=self.sample_rate,
            energy_threshold=self.energy_threshold,
            silence_duration=self.silence_duration,
        )

        # Pre-roll ring buffer: store last ~400ms before speech detected
        # so initial consonants are preserved perfectly
        preroll_count = 4
        preroll_buffer: collections.deque[np.ndarray] = collections.deque(maxlen=preroll_count)

        recorded_chunks: list[np.ndarray] = []
        speech_started = False
        start_time: float | None = None

        with mic.recorder(samplerate=self.sample_rate, channels=1, blocksize=self.block_size) as rec:
            import time

            start_time = time.time()
            while True:
                if stop_event and stop_event.is_set():
                    break

                # Read 100ms audio chunk
                raw_chunk = rec.record(numframes=self.block_size)
                mono_chunk = self.to_mono(raw_chunk)

                if manual_mode:
                    if not speech_started:
                        speech_started = True
                        if on_speech_started:
                            on_speech_started()
                    recorded_chunks.append(mono_chunk)
                    rms = vad.calculate_rms(mono_chunk)
                    elapsed = time.time() - start_time
                    if on_chunk:
                        on_chunk(SpeechState.SPEAKING, rms, elapsed)
                    continue

                state, rms = vad.process_chunk(mono_chunk)
                elapsed = time.time() - start_time

                if state in (SpeechState.SPEAKING, SpeechState.PAUSED):
                    if not speech_started:
                        speech_started = True
                        if on_speech_started:
                            on_speech_started()
                        # Include pre-roll chunks
                        recorded_chunks.extend(list(preroll_buffer))
                    recorded_chunks.append(mono_chunk)
                elif not speech_started:
                    preroll_buffer.append(mono_chunk)

                if on_chunk:
                    on_chunk(state, rms, elapsed)

                if state in (SpeechState.COMPLETED, SpeechState.TIMEOUT):
                    break

        if not recorded_chunks:
            return np.array([], dtype=np.float32), 0.0, speech_started

        full_audio = np.concatenate(recorded_chunks, axis=0)
        duration = len(full_audio) / self.sample_rate
        return full_audio, duration, speech_started
