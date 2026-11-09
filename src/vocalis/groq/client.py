"""Groq client initialization and authentication helper."""

from __future__ import annotations

from typing import Optional
import groq

from vocalis.config import VocalisConfig


class GroqAuthError(Exception):
    """Raised when Groq API key is missing or invalid."""
    pass


def get_groq_client(config: Optional[VocalisConfig] = None) -> groq.Groq:
    """Initialize and return a Groq API client."""
    if config is None:
        config = VocalisConfig.load()

    api_key = config.get_effective_api_key()
    if not api_key:
        raise GroqAuthError(
            "Groq API key not found!\n"
            "Please provide your API key by running:\n"
            "    vocalis config set groq_api_key <YOUR_GROQ_API_KEY>\n"
            "or set the environment variable:\n"
            "    export GROQ_API_KEY=<YOUR_GROQ_API_KEY>"
        )

    return groq.Groq(api_key=api_key)
