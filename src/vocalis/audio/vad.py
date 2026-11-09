"""Voice Activity Detection and energy analysis."""

from __future__ import annotations

import enum
import time
import numpy as np


class SpeechState(str, enum.Enum):
    """Current state of voice activity."""
    IDLE = "idle"                        # Waiting for initial speech
    SPEAKING = "speaking"                # Speech in progress
    PAUSED = "paused"                    # Speech occurred, currently silent (counting down timeout)
    COMPLETED = "completed"              # Silence duration reached after speech
    TIMEOUT = "timeout"                  # Max duration reached


class VADDetector:
    """Energy-based voice activity detector with adaptive noise floor and silence hangover."""

    def __init__(
        self,
        sample_rate: int = 16000,
        energy_threshold: float = 0.012,
        silence_duration: float = 0.9,
        min_record_seconds: float = 0.4,
        max_record_seconds: float = 90.0,
    ) -> None:
        self.sample_rate = sample_rate
        self.base_threshold = energy_threshold
        self.silence_duration = silence_duration
        self.min_record_seconds = min_record_seconds
        self.max_record_seconds = max_record_seconds

        self.state = SpeechState.IDLE
        self.noise_floor = 0.005
        self.speech_start_time: float | None = None
        self.silence_start_time: float | None = None
        self.total_speech_frames: int = 0
        self.calibration_chunks: int = 0

    @staticmethod
    def calculate_rms(audio_chunk: np.ndarray) -> float:
        """Calculate Root Mean Square (RMS) energy of an audio chunk."""
        if audio_chunk.size == 0:
            return 0.0
        # If stereo, flatten or take mean across channels
        if audio_chunk.ndim > 1:
            audio_chunk = np.mean(audio_chunk, axis=1)
        return float(np.sqrt(np.mean(audio_chunk.astype(np.float32) ** 2)))

    def get_effective_threshold(self) -> float:
        """Dynamic threshold based on base setting and tracked noise floor."""
        return max(self.base_threshold, self.noise_floor * 2.5)

    def process_chunk(self, audio_chunk: np.ndarray) -> tuple[SpeechState, float]:
        """Process an incoming audio chunk (e.g. 100ms) and return (new_state, rms)."""
        rms = self.calculate_rms(audio_chunk)
        now = time.time()

        # Initial calibration of ambient noise floor (first 4 chunks)
        if self.calibration_chunks < 4:
            self.noise_floor = (self.noise_floor * self.calibration_chunks + rms) / (self.calibration_chunks + 1)
            self.calibration_chunks += 1
            return SpeechState.IDLE, rms

        effective_threshold = self.get_effective_threshold()
        is_speech = rms >= effective_threshold

        # Adapt ambient noise floor slowly if not speaking
        if not is_speech and self.state == SpeechState.IDLE:
            self.noise_floor = 0.95 * self.noise_floor + 0.05 * rms

        if is_speech:
            if self.state in (SpeechState.IDLE, SpeechState.PAUSED):
                if self.speech_start_time is None:
                    self.speech_start_time = now
                self.silence_start_time = None
                self.state = SpeechState.SPEAKING
            self.total_speech_frames += len(audio_chunk)

        else:
            # Silence detected
            if self.state == SpeechState.SPEAKING:
                self.state = SpeechState.PAUSED
                self.silence_start_time = now

            elif self.state == SpeechState.PAUSED and self.silence_start_time is not None:
                elapsed_silence = now - self.silence_start_time
                speech_duration = (self.total_speech_frames / self.sample_rate)

                # Check if we have spoken enough and silence exceeded threshold
                if elapsed_silence >= self.silence_duration:
                    if speech_duration >= self.min_record_seconds:
                        self.state = SpeechState.COMPLETED
                    else:
                        # Spurious noise, reset
                        self.reset()

        # Check max recording duration
        if self.speech_start_time and (now - self.speech_start_time) >= self.max_record_seconds:
            self.state = SpeechState.TIMEOUT

        return self.state, rms

    def reset(self) -> None:
        """Reset the detector state for next utterance."""
        self.state = SpeechState.IDLE
        self.speech_start_time = None
        self.silence_start_time = None
        self.total_speech_frames = 0
