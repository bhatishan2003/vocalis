"""Command Line Interface for Vocalis."""

from __future__ import annotations

import os
import signal
import sys
import time
from typing import Optional

import click
from rich.table import Table

# Install top-level signal handler so Ctrl+C ALWAYS exits cleanly from any state
def handle_sigint(signum, frame):
    try:
        from vocalis.ui.display import clear_listening_line, ui_console
        clear_listening_line()
        ui_console.print("\n[bold yellow]👋 Stopped listening. Goodbye![/bold yellow]")
    except Exception:
        pass
    sys.exit(0)

try:
    signal.signal(signal.SIGINT, handle_sigint)
    signal.signal(signal.SIGTERM, handle_sigint)
except Exception:
    pass

from vocalis.audio.recorder import AudioRecorder
from vocalis.audio.vad import SpeechState
from vocalis.config import VocalisConfig
from vocalis.core import VocalisPipeline
from vocalis.ui.display import (
    clear_listening_line,
    print_banner,
    print_listening_status,
    ui_console,
)


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version="0.1.0", prog_name="vocalis")
def cli(ctx: click.Context) -> None:
    """🎙️ Vocalis: Wispr Flow-inspired AI voice dictation for developers."""
    if ctx.invoked_subcommand is None:
        # If no subcommand given, default to running start
        ctx.invoke(start)


@cli.command()
@click.option(
    "--mode",
    "-m",
    type=click.Choice(["prose", "code", "prompt", "raw"], case_sensitive=False),
    default=None,
    help="Refinement mode: prose (clean text), code (syntax/formatting), prompt (AI instructions), or raw.",
)
@click.option(
    "--continuous",
    "-c",
    is_flag=True,
    default=True,
    help="Continuously listen and type thoughts in a loop (default: True).",
)
@click.option(
    "--once",
    "-1",
    is_flag=True,
    default=False,
    help="Record a single thought, type/copy it, and exit immediately.",
)
@click.option(
    "--no-type",
    is_flag=True,
    default=False,
    help="Do not type text directly into the focused window (clipboard only).",
)
@click.option(
    "--type-method",
    type=click.Choice(["type", "paste"], case_sensitive=False),
    default="type",
    help="Injection method: 'type' (direct simulated keystrokes) or 'paste' (Ctrl+V).",
)
@click.option(
    "--sound/--no-sound",
    default=True,
    help="Enable or disable audio cue chimes when listening starts and completes.",
)
@click.option(
    "--stream/--no-stream",
    default=True,
    help="Stream tokens directly to active cursor as LLM generates them.",
)
@click.option(
    "--model",
    default=None,
    help="Groq LLM model override (e.g. openai/gpt-oss-120b, llama-3.3-70b-versatile, llama-3.1-8b-instant).",
)
@click.option(
    "--stt-model",
    default=None,
    help="Groq STT model override (e.g. whisper-large-v3-turbo, whisper-large-v3).",
)
@click.option(
    "--language",
    "-l",
    default=None,
    help="Spoken language code (e.g. 'en', 'es', 'fr', 'de') or 'auto'.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    default=False,
    help="Quiet mode: suppress UI banners and print only the final text to stdout.",
)
@click.option(
    "--file",
    "-f",
    "target_file",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Append the transcribed output to the specified file.",
)
@click.option(
    "--show-raw",
    is_flag=True,
    default=False,
    help="Show both the raw Whisper transcript and the refined output.",
)
@click.option(
    "--no-copy",
    is_flag=True,
    default=False,
    help="Do not copy the output to the system clipboard.",
)
@click.option(
    "--manual",
    is_flag=True,
    default=False,
    help="Manual mode: Press Enter to stop recording instead of waiting for silence detection.",
)
def start(
    mode: Optional[str],
    continuous: bool,
    once: bool,
    no_type: bool,
    type_method: str,
    sound: bool,
    stream: bool,
    model: Optional[str],
    stt_model: Optional[str],
    language: Optional[str],
    quiet: bool,
    target_file: Optional[str],
    show_raw: bool,
    no_copy: bool,
    manual: bool,
) -> None:
    """🎙️ Start listening to voice and type/refine everywhere you point your cursor."""
    config = VocalisConfig.load()
    active_mode = mode or config.default_mode
    active_model = model or config.llm_model

    if not quiet:
        print_banner(mode=active_mode, model=active_model)
        ui_console.print(
            "  [bold green]● Direct screen typing is ACTIVE[/bold green]\n"
            "  [cyan]👉 Point your cursor into VS Code, Antigravity, or any app and speak.[/cyan]\n"
            "  [dim]Text will type at your cursor. Press Enter (while idle) or Ctrl+C to stop.[/dim]\n"
        )

    pipeline = VocalisPipeline(config=config)

    # By default, run continuously in a loop unless --once is requested
    loop_mode = not once

    try:
        while True:
            result = pipeline.process_utterance(
                mode=active_mode,
                llm_model=active_model,
                stt_model=stt_model,
                language=language,
                copy_clipboard=not no_copy,
                auto_type=not no_type,
                type_method=type_method,
                show_raw=show_raw,
                quiet=quiet,
                target_file=target_file,
                manual_mode=manual,
                enable_sound=sound,
                enable_stream=stream,
            )

            # If user pressed Enter while idle, cleanly exit
            if result and result.get("action") == "exit":
                if not quiet:
                    ui_console.print("\n[dim]Enter pressed while idle. Stopped listening.[/dim]")
                break

            if not loop_mode:
                break

            if not quiet and result is not None:
                ui_console.print("[dim]─" * 40 + "[/dim]")

    except (KeyboardInterrupt, SystemExit):
        clear_listening_line()
        if not quiet:
            ui_console.print("\n[dim]Stopped listening.[/dim]")
        sys.exit(0)


@cli.group()
def config() -> None:
    """⚙️ Manage Vocalis settings and Groq API keys."""
    pass


@config.command("show")
def config_show() -> None:
    """Display current configuration."""
    cfg = VocalisConfig.load()

    table = Table(title="Vocalis Configuration", border_style="cyan")
    table.add_column("Setting", style="bold white")
    table.add_column("Value", style="cyan")
    table.add_column("Source", style="dim")

    key = cfg.get_effective_api_key()
    if key:
        masked_key = f"{key[:7]}...{key[-4:]}" if len(key) > 12 else "********"
        source = "Environment ($GROQ_API_KEY)" if os.environ.get("GROQ_API_KEY") else "config.json"
        table.add_row("Groq API Key", masked_key, source)
    else:
        table.add_row("Groq API Key", "[red]Not configured[/red]", "Run: vocalis config set groq_api_key <key>")

    table.add_row("Default Mode", cfg.default_mode, "config.json")
    table.add_row("STT Model", cfg.stt_model, "config.json")
    table.add_row("LLM Model", cfg.llm_model, "config.json")
    table.add_row("Language", cfg.language, "config.json")
    table.add_row("Silence Timeout", f"{cfg.silence_duration}s", "config.json")
    table.add_row("Energy Threshold", str(cfg.energy_threshold), "config.json")
    table.add_row("Auto Copy", str(cfg.auto_copy), "config.json")
    table.add_row("Auto Type", str(cfg.auto_type), "config.json")
    table.add_row("Stream Typing", str(cfg.stream_typing), "config.json")
    table.add_row("Sound Effects", str(cfg.sound_effects), "config.json")
    table.add_row("Vocabulary", ", ".join(cfg.custom_vocabulary[:5]) + ("..." if len(cfg.custom_vocabulary) > 5 else ""), "config.json")
    table.add_row("Input Device", cfg.input_device or "[dim]System Default[/dim]", "config.json")

    ui_console.print(table)


@cli.group()
def vocab() -> None:
    """📚 Manage custom boosted vocabulary for Whisper STT."""
    pass


@vocab.command("list")
def vocab_list() -> None:
    """List all custom keywords boosted during transcription."""
    cfg = VocalisConfig.load()
    if not cfg.custom_vocabulary:
        ui_console.print("[dim]No custom vocabulary configured. Run `vocalis vocab add <word>` to add.[/dim]")
        return

    table = Table(title="Boosted Vocabulary Words", border_style="cyan")
    table.add_column("Index", style="dim", width=6)
    table.add_column("Word / Term", style="bold white")

    for i, word in enumerate(cfg.custom_vocabulary):
        table.add_row(str(i + 1), word)

    ui_console.print(table)


@vocab.command("add")
@click.argument("words", nargs=-1, required=True)
def vocab_add(words: tuple[str, ...]) -> None:
    """Add one or more words to custom vocabulary (e.g. vocalis vocab add FastAPI Kubelet)."""
    cfg = VocalisConfig.load()
    added = []
    for w in words:
        clean = w.strip()
        if clean and clean not in cfg.custom_vocabulary:
            cfg.custom_vocabulary.append(clean)
            added.append(clean)

    if added:
        cfg.save()
        ui_console.print(f"[bold green]✓[/bold green] Added to vocabulary: [cyan]{', '.join(added)}[/cyan]")
    else:
        ui_console.print("[yellow]Words already present in vocabulary.[/yellow]")


@vocab.command("remove")
@click.argument("word")
def vocab_remove(word: str) -> None:
    """Remove a word from custom vocabulary."""
    cfg = VocalisConfig.load()
    match = [w for w in cfg.custom_vocabulary if w.lower() == word.lower()]
    if not match:
        ui_console.print(f"[yellow]Word '{word}' not found in vocabulary.[/yellow]")
        return

    for m in match:
        cfg.custom_vocabulary.remove(m)
    cfg.save()
    ui_console.print(f"[bold green]✓[/bold green] Removed '{match[0]}' from vocabulary.")


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    """Set a configuration option (e.g. vocalis config set groq_api_key gsk_...)."""
    cfg = VocalisConfig.load()
    key_norm = key.lower().replace("-", "_")

    if not hasattr(cfg, key_norm):
        ui_console.print(f"[bold red]Unknown setting:[/bold red] '{key}'. Run `vocalis config show` for valid keys.")
        return

    # Type casting
    field_type = type(getattr(cfg, key_norm))
    try:
        if field_type is bool:
            typed_value = value.lower() in ("true", "1", "yes", "on")
        elif field_type is float:
            typed_value = float(value)
        elif field_type is int:
            typed_value = int(value)
        else:
            typed_value = value
    except ValueError as e:
        ui_console.print(f"[bold red]Invalid value format for {key}:[/bold red] {e}")
        return

    setattr(cfg, key_norm, typed_value)
    cfg.save()
    ui_console.print(f"[bold green]✓[/bold green] Updated [cyan]{key_norm}[/cyan] = [bold]{typed_value}[/bold]")


@cli.command("test-mic")
@click.option("--seconds", "-s", default=8, help="Number of seconds to test microphone.")
def test_mic(seconds: int) -> None:
    """🎤 Test microphone input and calibrate ambient noise levels."""
    config = VocalisConfig.load()
    recorder = AudioRecorder(sample_rate=config.sample_rate, energy_threshold=config.energy_threshold)

    ui_console.print("[bold cyan]Testing microphone input... Speak into your mic.[/bold cyan]")
    ui_console.print(f"[dim]Device: {recorder.get_microphone().name}[/dim]")
    ui_console.print("[dim]Press Ctrl+C to finish early.[/dim]\n")

    max_energy = 0.0

    def on_chunk(state: SpeechState, rms: float, elapsed: float):
        nonlocal max_energy
        if rms > max_energy:
            max_energy = rms
        print_listening_status(state, rms, elapsed)

    import threading
    stop_event = threading.Event()

    def timer():
        time.sleep(seconds)
        stop_event.set()

    t = threading.Thread(target=timer, daemon=True)
    t.start()

    try:
        recorder.record_utterance(on_chunk=on_chunk, stop_event=stop_event, manual_mode=True)
    except KeyboardInterrupt:
        pass
    finally:
        clear_listening_line()

    ui_console.print("[bold green]✓ Microphone test complete.[/bold green]")
    ui_console.print(f"  • Peak RMS Volume: [cyan]{max_energy:.4f}[/cyan]")
    ui_console.print(f"  • Configured Threshold: [dim]{config.energy_threshold}[/dim]")

    if max_energy < 0.005:
        ui_console.print("  [yellow]⚠️ Peak volume was very low. Check your system input volume or select another mic.[/yellow]")
    else:
        ui_console.print("  [bold green]✓ Microphone level looks healthy![/bold green]")


@cli.command("list-devices")
def list_devices() -> None:
    """🔊 List all available input microphones."""
    devices = AudioRecorder.list_devices()
    if not devices:
        ui_console.print("[yellow]No audio input devices detected.[/yellow]")
        return

    table = Table(title="Available Audio Input Devices", border_style="cyan")
    table.add_column("Index", style="dim", width=6)
    table.add_column("Device Name", style="bold white")

    for i, dev in enumerate(devices):
        table.add_row(str(i), dev)

    ui_console.print(table)


@cli.command("setup-editor")
def setup_editor() -> None:
    """💻 Show editor setup instructions and keybindings for VS Code & Neovim."""
    from rich.markdown import Markdown

    doc = """
# Vocalis Editor Setup Guide

### 1. VS Code / Cursor Integration

You can trigger Vocalis with a single keybinding (e.g. `Ctrl+Alt+V` or `Cmd+Shift+V`):

#### A. Add a task in `.vscode/tasks.json` (or User Tasks):
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Vocalis: Dictate",
      "type": "shell",
      "command": "uv run --directory /home/ishan/vocalis vocalis start --once",
      "presentation": {
        "reveal": "always",
        "panel": "shared",
        "focus": true
      },
      "problemMatcher": []
    }
  ]
}
```

#### B. Bind to a keyboard shortcut in `keybindings.json`:
```json
[
  {
    "key": "ctrl+alt+v",
    "command": "workbench.action.tasks.runTask",
    "args": "Vocalis: Dictate"
  }
]
```

---

### 2. Neovim Integration (Lua)

Add this snippet to your `init.lua`:

```lua
-- Dictate into system clipboard and paste at cursor
vim.keymap.set({"n", "i"}, "<C-g><C-v>", function()
  vim.notify("🎙️ Vocalis listening...", vim.log.levels.INFO)
  vim.fn.jobstart({"uv", "run", "--directory", "/home/ishan/vocalis", "vocalis", "start", "--once", "--quiet"}, {
    on_exit = function()
      vim.schedule(function()
        vim.cmd("normal! p")
        vim.notify("📋 Dictation pasted!", vim.log.levels.INFO)
      end)
    end,
  })
end, { desc = "Vocalis Dictate & Paste" })
```

---

### 3. Quick Terminal Aliases

Add these to your `~/.bashrc` or `~/.zshrc`:
```bash
alias vstart="uv run --directory /home/ishan/vocalis vocalis start"
alias vcode="uv run --directory /home/ishan/vocalis vocalis start --mode code"
alias vprompt="uv run --directory /home/ishan/vocalis vocalis start --mode prompt"
```
"""
    ui_console.print(Markdown(doc))


def main() -> None:
    """Entry point for project console script."""
    cli()


if __name__ == "__main__":
    main()
