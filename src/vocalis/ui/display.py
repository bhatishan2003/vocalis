"""Terminal UI and real-time visual feedback using Rich."""

from __future__ import annotations

import sys
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from vocalis.audio.vad import SpeechState


# Console for interactive UI (output to stderr so stdout can be piped cleanly)
ui_console = Console(stderr=True)
out_console = Console()


def render_vu_meter(rms: float, max_rms: float = 0.08, width: int = 15) -> str:
    """Generate a responsive unicode VU meter bar based on RMS volume."""
    levels = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    ratio = min(1.0, max(0.0, rms / max_rms))
    filled_len = int(ratio * width)
    meter = ""
    for i in range(width):
        if i < filled_len:
            meter += "█"
        elif i == filled_len:
            idx = int((ratio * width - filled_len) * len(levels))
            meter += levels[min(idx, len(levels) - 1)]
        else:
            meter += "░"
    return meter


def get_state_badge(state: SpeechState) -> str:
    """Format a styled state badge for the current audio state."""
    if state == SpeechState.SPEAKING:
        return "[bold green]● SPEAKING [/bold green]"
    if state == SpeechState.PAUSED:
        return "[bold yellow]⏸ SILENCE  [/bold yellow]"
    if state == SpeechState.COMPLETED:
        return "[bold cyan]✓ FINISHED [/bold cyan]"
    return "[dim]○ LISTENING[/dim]"


def print_banner(mode: str, model: str) -> None:
    """Print the Vocalis header banner."""
    ui_console.print(
        f"[bold white on blue] 🎙️  Vocalis [/bold white on blue]  "
        f"Mode: [bold cyan]{mode.upper()}[/bold cyan]  |  LLM: [dim]{model}[/dim]\n"
    )


def print_listening_status(state: SpeechState, rms: float, elapsed: float) -> None:
    """Render single-line live microphone status with VU meter."""
    badge = get_state_badge(state)
    meter = render_vu_meter(rms)
    ui_console.print(
        f"\r  {badge} [cyan][{meter}][/cyan]  [dim]{elapsed:04.1f}s[/dim]  [dim](Press Enter or Ctrl+C to stop)[/dim]  ",
        end="",
    )


def clear_listening_line() -> None:
    """Clear the single-line listening prompt."""
    ui_console.print("\r" + " " * 80 + "\r", end="")


def print_processing(stage: str) -> None:
    """Print processing stage indicator."""
    clear_listening_line()
    if stage == "transcribing":
        ui_console.print("  [bold yellow]⚡ Transcribing audio via Groq Whisper...[/bold yellow]")
    elif stage == "refining":
        ui_console.print("  [bold magenta]✨ Polishing with Groq LLM...[/bold magenta]")


def print_result_card(
    refined_text: str,
    raw_text: Optional[str] = None,
    mode: str = "prose",
    stt_ms: float = 0.0,
    llm_ms: float = 0.0,
    clipboard_backends: Optional[list[str]] = None,
    typed: bool = False,
    show_raw: bool = False,
) -> None:
    """Display the finalized result card with timings and formatted output."""
    total_ms = stt_ms + llm_ms

    timing_info = f"⚡ STT: {stt_ms:.0f}ms | ✨ LLM: {llm_ms:.0f}ms | ⏱️ Total: {total_ms:.0f}ms"
    status_tags = []
    if clipboard_backends:
        status_tags.append("📋 [bold green]Copied[/bold green]")
    if typed:
        status_tags.append("⌨️ [bold green]Typed into Window[/bold green]")

    tag_str = f"  •  {'  •  '.join(status_tags)}" if status_tags else ""
    subtitle = f"[dim]{timing_info}[/dim]{tag_str}"

    if mode == "code" and ("```" not in refined_text) and any(kw in refined_text for kw in ("def ", "class ", "import ", "const ", "let ", "function ")):
        content = Syntax(refined_text, "python", theme="monokai", line_numbers=False)
    else:
        content = Text(refined_text)

    panel = Panel(
        content,
        title=f"[bold cyan]Vocalis Output ({mode.upper()})[/bold cyan]",
        subtitle=subtitle,
        border_style="cyan",
        padding=(1, 2),
    )
    ui_console.print(panel)

    if show_raw and raw_text and raw_text != refined_text:
        ui_console.print(f"[dim]Raw Whisper:[/dim] [italic dim]{raw_text}[/italic dim]\n")
