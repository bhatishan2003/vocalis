"""Audio transcription via Groq Whisper API."""

from __future__ import annotations

import time
from typing import Optional
import groq

from vocalis.config import VocalisConfig
from vocalis.groq.client import get_groq_client


class GroqTranscriber:
    """Handles Speech-to-Text transcription via Groq's high-speed Whisper models."""

    def __init__(self, config: Optional[VocalisConfig] = None) -> None:
        self.config = config or VocalisConfig.load()
        self.client = get_groq_client(self.config)

    def transcribe(
        self,
        wav_bytes: bytes,
        model: Optional[str] = None,
        language: Optional[str] = None,
    ) -> tuple[str, float]:
        """Transcribe WAV audio bytes to text using Groq Whisper.

        Args:
            wav_bytes: In-memory WAV audio file bytes.
            model: Whisper model override (default from config).
            language: Language code (e.g. 'en') or None for auto-detect.

        Returns:
            Tuple of (transcribed_text, latency_in_ms)
        """
        stt_model = model or self.config.stt_model
        lang = language if language is not None else self.config.language

        start_time = time.perf_counter()

        # Build parameters
        params: dict = {
            "file": ("audio.wav", wav_bytes, "audio/wav"),
            "model": stt_model,
            "response_format": "text",
        }
        if lang and lang.lower() != "auto":
            params["language"] = lang

        # Add custom vocabulary keyword boosting
        if self.config.custom_vocabulary:
            params["prompt"] = ", ".join(self.config.custom_vocabulary)

        response = self.client.audio.transcriptions.create(**params)
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        if isinstance(response, str):
            text = response.strip()
        else:
            text = getattr(response, "text", str(response)).strip()

        return text, latency_ms
