"""Configuration management for Vocalis."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional


CONFIG_DIR = Path.home() / ".config" / "vocalis"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_dotenv_file() -> None:
    """Load key-value pairs from a local .env file into os.environ if present."""
    proj_root = Path(__file__).resolve().parent.parent.parent
    candidates = [
        Path.cwd() / ".env",
        Path.cwd() / ".env_example",
        Path.cwd() / ".env.example",
        Path.home() / ".config" / "vocalis" / ".env",
        Path.home() / ".config" / "vocalis" / ".env_example",
        proj_root / ".env",
        proj_root / ".env_example",
    ]
    for env_path in candidates:
        if env_path.is_file():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        # Ignore placeholder template values
                        if k == "GROQ_API_KEY" and ("your_groq_api_key" in v.lower() or not v):
                            continue
                        if k and k not in os.environ:
                            os.environ[k] = v
            except Exception:
                pass


@dataclass
class VocalisConfig:
    """Configuration settings for Vocalis."""

    groq_api_key: Optional[str] = None
    stt_model: str = "whisper-large-v3-turbo"
    llm_model: str = "openai/gpt-oss-120b"
    default_mode: str = "prose"  # 'prose', 'code', 'prompt', 'raw'
    language: str = "en"
    silence_duration: float = 0.9  # Seconds of silence before auto-stopping
    energy_threshold: float = 0.012  # RMS threshold for voice activity
    sample_rate: int = 16000
    min_record_seconds: float = 0.4
    max_record_seconds: float = 90.0
    auto_copy: bool = True
    auto_type: bool = True
    type_method: str = "type"  # 'type' (direct keys) or 'paste' (Ctrl+V)
    type_delay: float = 0.001
    append_space: bool = True
    sound_effects: bool = True
    stream_typing: bool = True
    custom_vocabulary: list[str] = field(
        default_factory=lambda: [
            "Vocalis",
            "Groq",
            "Ishan",
            "uv",
            "CLI",
            "VS Code",
            "Neovim",
            "API",
            "JSON",
            "Python",
        ]
    )
    input_device: Optional[str] = None

    @classmethod
    def load(cls) -> VocalisConfig:
        """Load configuration from disk, falling back to environment variables and defaults."""
        load_dotenv_file()

        data: dict[str, Any] = {}
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}

        # Environment variable overrides
        env_key = os.environ.get("GROQ_API_KEY")
        if env_key:
            data["groq_api_key"] = env_key

        if "VOCALIS_MODE" in os.environ:
            data["default_mode"] = os.environ["VOCALIS_MODE"]

        if "VOCALIS_LLM_MODEL" in os.environ:
            data["llm_model"] = os.environ["VOCALIS_LLM_MODEL"]

        if "VOCALIS_STT_MODEL" in os.environ:
            data["stt_model"] = os.environ["VOCALIS_STT_MODEL"]

        if "VOCALIS_SILENCE_DURATION" in os.environ:
            try:
                data["silence_duration"] = float(os.environ["VOCALIS_SILENCE_DURATION"])
            except ValueError:
                pass

        if "VOCALIS_LANGUAGE" in os.environ:
            data["language"] = os.environ["VOCALIS_LANGUAGE"]

        if "VOCALIS_ENERGY_THRESHOLD" in os.environ:
            try:
                data["energy_threshold"] = float(os.environ["VOCALIS_ENERGY_THRESHOLD"])
            except ValueError:
                pass

        if "VOCALIS_AUTO_TYPE" in os.environ:
            data["auto_type"] = os.environ["VOCALIS_AUTO_TYPE"].lower() in ("true", "1", "yes", "on")

        if "VOCALIS_TYPE_METHOD" in os.environ:
            data["type_method"] = os.environ["VOCALIS_TYPE_METHOD"]

        if "VOCALIS_SOUND_EFFECTS" in os.environ:
            data["sound_effects"] = os.environ["VOCALIS_SOUND_EFFECTS"].lower() in ("true", "1", "yes", "on")

        if "VOCALIS_STREAM_TYPING" in os.environ:
            data["stream_typing"] = os.environ["VOCALIS_STREAM_TYPING"].lower() in ("true", "1", "yes", "on")

        if "VOCALIS_VOCABULARY" in os.environ:
            data["custom_vocabulary"] = [
                v.strip() for v in os.environ["VOCALIS_VOCABULARY"].split(",") if v.strip()
            ]

        # Filter valid fields
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def save(self) -> None:
        """Save current configuration to disk."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    def get_effective_api_key(self) -> Optional[str]:
        """Return the API key from environment variable or stored configuration."""
        return os.environ.get("GROQ_API_KEY") or self.groq_api_key
