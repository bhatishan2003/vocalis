"""Tests for Groq STT and LLM refiner using mock responses."""

from unittest.mock import MagicMock
from vocalis.config import VocalisConfig
from vocalis.groq.refiner import GroqRefiner
from vocalis.groq.transcriber import GroqTranscriber


def test_transcriber_mock(monkeypatch):
    cfg = VocalisConfig(groq_api_key="gsk_mock_key")
    transcriber = GroqTranscriber(cfg)

    mock_response = "Hello this is a test transcription."
    monkeypatch.setattr(
        transcriber.client.audio.transcriptions,
        "create",
        MagicMock(return_value=mock_response),
    )

    text, latency = transcriber.transcribe(b"fake_wav_bytes")
    assert text == mock_response
    assert latency >= 0.0


def test_refiner_mock(monkeypatch):
    cfg = VocalisConfig(groq_api_key="gsk_mock_key")
    refiner = GroqRefiner(cfg)

    # 1. Raw mode bypasses API call
    raw_text, latency = refiner.refine("um hello world", mode="raw")
    assert raw_text == "um hello world"
    assert latency == 0.0

    # 2. Prose mode calls LLM
    mock_choice = MagicMock()
    mock_choice.message.content = "Hello world."
    mock_resp = MagicMock(choices=[mock_choice])

    monkeypatch.setattr(
        refiner.client.chat.completions,
        "create",
        MagicMock(return_value=mock_resp),
    )

    refined, latency = refiner.refine("um hello world", mode="prose")
    assert refined == "Hello world."
    assert latency >= 0.0
