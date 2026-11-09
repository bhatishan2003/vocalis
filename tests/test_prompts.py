"""Tests for refinement prompts."""

from vocalis.groq.prompts import SYSTEM_PROMPTS, get_prompt_for_mode


def test_modes_exist():
    assert "prose" in SYSTEM_PROMPTS
    assert "code" in SYSTEM_PROMPTS
    assert "prompt" in SYSTEM_PROMPTS
    assert "raw" in SYSTEM_PROMPTS


def test_prompt_rules():
    prose = get_prompt_for_mode("prose")
    assert "Wispr Flow" in prose
    assert "filler words" in prose.lower()

    code = get_prompt_for_mode("code")
    assert "code" in code.lower()

    prompt = get_prompt_for_mode("prompt")
    assert "prompt" in prompt.lower()

    # Fallback mode
    unknown = get_prompt_for_mode("unknown_mode")
    assert unknown == SYSTEM_PROMPTS["prose"]
