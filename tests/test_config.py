"""Tests for configuration management."""

import os
from vocalis.config import VocalisConfig


def test_default_config():
    cfg = VocalisConfig()
    assert cfg.default_mode == "prose"
    assert cfg.stt_model == "whisper-large-v3-turbo"
    assert cfg.llm_model == "openai/gpt-oss-120b"
    assert cfg.language == "en"
    assert cfg.auto_copy is True


def test_env_var_override(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_key_12345")
    monkeypatch.setenv("VOCALIS_MODE", "code")
    monkeypatch.setenv("VOCALIS_SILENCE_DURATION", "1.5")

    cfg = VocalisConfig.load()
    assert cfg.get_effective_api_key() == "gsk_test_key_12345"
    assert cfg.default_mode == "code"
    assert cfg.silence_duration == 1.5


def test_config_save_and_load(tmp_path, monkeypatch):
    test_file = tmp_path / "config.json"
    monkeypatch.setattr("vocalis.config.CONFIG_FILE", test_file)
    monkeypatch.setattr("vocalis.config.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("vocalis.config.load_dotenv_file", lambda: None)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    cfg = VocalisConfig(groq_api_key="gsk_custom_saved_key", default_mode="prompt")
    cfg.save()

    loaded = VocalisConfig.load()
    assert loaded.groq_api_key == "gsk_custom_saved_key"
    assert loaded.default_mode == "prompt"


def test_load_dotenv_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("GROQ_API_KEY=gsk_from_dotenv_test\nVOCALIS_MODE=prompt\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("VOCALIS_MODE", raising=False)

    cfg = VocalisConfig.load()
    assert cfg.get_effective_api_key() == "gsk_from_dotenv_test"
    assert cfg.default_mode == "prompt"
