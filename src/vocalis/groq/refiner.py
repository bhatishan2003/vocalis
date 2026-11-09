"""Wispr Flow-inspired text refinement using Groq LLMs."""

from __future__ import annotations

import time
from typing import Callable, Optional

from vocalis.config import VocalisConfig
from vocalis.groq.client import get_groq_client
from vocalis.groq.prompts import get_prompt_for_mode


class GroqRefiner:
    """Refines raw Whisper transcripts into polished prose, code, or prompts."""

    def __init__(self, config: Optional[VocalisConfig] = None) -> None:
        self.config = config or VocalisConfig.load()
        self.client = get_groq_client(self.config)

    def refine(
        self,
        raw_text: str,
        mode: Optional[str] = None,
        model: Optional[str] = None,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> tuple[str, float]:
        """Refine raw transcript using Groq LLM.

        Args:
            raw_text: Raw transcription output from Whisper.
            mode: Refinement mode ('prose', 'code', 'prompt', 'raw').
            model: Groq LLM model override.
            on_token: Optional streaming callback called with each token chunk.

        Returns:
            Tuple of (refined_text, latency_in_ms)
        """
        active_mode = (mode or self.config.default_mode).lower()

        # If empty text or raw mode, skip LLM
        if not raw_text.strip() or active_mode == "raw":
            if on_token:
                on_token(raw_text.strip())
            return raw_text.strip(), 0.0

        system_prompt = get_prompt_for_mode(active_mode)
        llm_model = model or self.config.llm_model

        start_time = time.perf_counter()

        # Streaming mode
        if on_token:
            response = self.client.chat.completions.create(
                model=llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": raw_text},
                ],
                temperature=0.2,
                max_tokens=2048,
                stream=True,
            )
            tokens: list[str] = []
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    delta = chunk.choices[0].delta.content
                    tokens.append(delta)
                    on_token(delta)

            latency_ms = (time.perf_counter() - start_time) * 1000.0
            refined = "".join(tokens).strip()
            return refined if refined else raw_text, latency_ms

        # Non-streaming fallback
        response = self.client.chat.completions.create(
            model=llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": raw_text},
            ],
            temperature=0.2,
            max_tokens=2048,
            stream=False,
        )
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        content = response.choices[0].message.content
        refined = content.strip() if content else raw_text

        # Strip accidental markdown code fence wrapper if LLM wrapped whole prose in ```markdown
        if active_mode == "prose" and refined.startswith("```") and refined.endswith("```"):
            lines = refined.split("\n")
            if len(lines) >= 3:
                refined = "\n".join(lines[1:-1]).strip()

        return refined, latency_ms
