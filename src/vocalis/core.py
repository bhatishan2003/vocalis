"""Core execution pipeline for Vocalis."""

from __future__ import annotations

import select
import sys
import threading
from typing import Any, Optional

from vocalis.audio.chime import ChimePlayer
from vocalis.audio.recorder import AudioRecorder
from vocalis.audio.vad import SpeechState
from vocalis.config import VocalisConfig
from vocalis.groq.client import GroqAuthError
from vocalis.groq.refiner import GroqRefiner
from vocalis.groq.transcriber import GroqTranscriber
from vocalis.output.clipboard import copy_to_clipboard
from vocalis.output.injector import TextInjector
from vocalis.ui.display import (
    clear_listening_line,
    print_listening_status,
    print_processing,
    print_result_card,
    ui_console,
)


class VocalisPipeline:
    """Manages the complete recording -> transcription -> refinement -> output pipeline."""

    def __init__(self, config: Optional[VocalisConfig] = None) -> None:
        self.config = config or VocalisConfig.load()
        self.recorder = AudioRecorder(
            sample_rate=self.config.sample_rate,
            device_name=self.config.input_device,
            silence_duration=self.config.silence_duration,
            energy_threshold=self.config.energy_threshold,
        )
        self.injector = TextInjector()
        self.chimes = ChimePlayer(enabled=self.config.sound_effects)

    def process_utterance(
        self,
        mode: Optional[str] = None,
        llm_model: Optional[str] = None,
        stt_model: Optional[str] = None,
        language: Optional[str] = None,
        copy_clipboard: bool = True,
        auto_type: bool = True,
        type_method: Optional[str] = None,
        show_raw: bool = False,
        quiet: bool = False,
        target_file: Optional[str] = None,
        manual_mode: bool = False,
        enable_sound: Optional[bool] = None,
        enable_stream: Optional[bool] = None,
    ) -> Optional[dict[str, Any]]:
        """Run a single capture-transcribe-refine cycle.

        Returns:
            Dict containing transcription and refinement details, or None if cancelled/empty.
        """
        active_mode = (mode or self.config.default_mode).lower()
        use_sound = self.config.sound_effects if enable_sound is None else enable_sound
        use_stream = self.config.stream_typing if enable_stream is None else enable_stream
        self.chimes.enabled = use_sound

        # Initialize Groq client early to catch missing API key before recording starts
        try:
            transcriber = GroqTranscriber(self.config)
            refiner = GroqRefiner(self.config)
        except GroqAuthError as e:
            ui_console.print(f"[bold red]Configuration Error:[/bold red] {e}")
            return None

        stop_event = threading.Event()
        user_stopped_manually = False

        # Thread to catch Enter key on stdin if running in interactive terminal
        def stdin_listener():
            nonlocal user_stopped_manually
            try:
                if sys.stdin.isatty():
                    while not stop_event.is_set():
                        # Use short select timeout to avoid deadlocks
                        r, _, _ = select.select([sys.stdin], [], [], 0.15)
                        if r:
                            sys.stdin.readline()
                            user_stopped_manually = True
                            stop_event.set()
                            break
            except Exception:
                pass

        listener_thread = threading.Thread(target=stdin_listener, daemon=True)
        listener_thread.start()

        def on_chunk(state: SpeechState, rms: float, elapsed: float):
            if not quiet:
                print_listening_status(state, rms, elapsed)

        def on_speech_started():
            self.chimes.play_start()

        try:
            audio_data, duration, speech_started = self.recorder.record_utterance(
                on_chunk=on_chunk,
                on_speech_started=on_speech_started,
                stop_event=stop_event,
                manual_mode=manual_mode,
            )
        except KeyboardInterrupt:
            stop_event.set()
            clear_listening_line()
            raise
        finally:
            stop_event.set()
            if not quiet:
                clear_listening_line()

        # If user pressed Enter before speaking anything, exit cleanly
        if user_stopped_manually and not speech_started:
            return {"action": "exit"}

        # Ignore accidental clicks / empty recording (< 0.25 seconds or 0 samples)
        if len(audio_data) < self.config.sample_rate * 0.25:
            if not quiet and speech_started:
                ui_console.print("[dim]Speech was too brief, skipped.[/dim]")
            return None

        # Convert to WAV bytes in memory
        wav_bytes = self.recorder.to_wav_bytes(audio_data, self.config.sample_rate)

        # 1. Transcribe via Groq Whisper
        if not quiet:
            print_processing("transcribing")

        try:
            raw_text, stt_ms = transcriber.transcribe(
                wav_bytes=wav_bytes,
                model=stt_model,
                language=language,
            )
        except Exception as e:
            clear_listening_line()
            ui_console.print(f"[bold red]Transcription failed:[/bold red] {e}")
            return None

        if not raw_text.strip():
            clear_listening_line()
            if not quiet:
                ui_console.print("[dim]Whisper did not detect any words.[/dim]")
            return None

        # 2. Refine via Groq LLM (Streaming directly to active cursor window)
        if active_mode != "raw" and not quiet:
            print_processing("refining")

        method = type_method or self.config.type_method
        should_stream_type = (
            use_stream
            and auto_type
            and self.config.auto_type
            and self.injector.is_available
            and method == "type"
            and active_mode != "raw"
        )

        streamed_tokens: list[str] = []

        def on_token(delta: str):
            streamed_tokens.append(delta)
            if should_stream_type:
                self.injector.type_text(delta, char_delay=0.0)

        try:
            refined_text, llm_ms = refiner.refine(
                raw_text=raw_text,
                mode=active_mode,
                model=llm_model,
                on_token=on_token if should_stream_type else None,
            )
        except Exception as e:
            clear_listening_line()
            ui_console.print(f"[yellow]LLM refinement warning (falling back to raw):[/yellow] {e}")
            refined_text = raw_text
            llm_ms = 0.0

        clear_listening_line()

        # 3. Handle Clipboard
        clipboard_backends: list[str] = []
        if copy_clipboard and self.config.auto_copy:
            clipboard_backends = copy_to_clipboard(refined_text)

        # 4. Handle Direct Keystroke Injection (if not already typed during streaming)
        typed_successfully = False
        if auto_type and self.config.auto_type and self.injector.is_available:
            if should_stream_type and streamed_tokens:
                # Already typed via stream, just append trailing space if configured
                if self.config.append_space and not refined_text.endswith((" ", "\n", "\t")):
                    self.injector.type_text(" ", char_delay=0.0)
                typed_successfully = True
            else:
                typed_successfully = self.injector.inject(
                    refined_text,
                    method=method,
                    append_space=self.config.append_space,
                    char_delay=self.config.type_delay,
                )

        # Play done chime
        self.chimes.play_done()

        # 5. Handle Target File
        if target_file:
            try:
                with open(target_file, "a", encoding="utf-8") as f:
                    f.write(refined_text + "\n")
            except Exception as e:
                ui_console.print(f"[yellow]Warning: Could not write to {target_file}:[/yellow] {e}")

        # 6. Output Display
        if quiet:
            print(refined_text)
        else:
            print_result_card(
                refined_text=refined_text,
                raw_text=raw_text,
                mode=active_mode,
                stt_ms=stt_ms,
                llm_ms=llm_ms,
                clipboard_backends=clipboard_backends,
                typed=typed_successfully,
                show_raw=show_raw,
            )

        return {
            "raw": raw_text,
            "refined": refined_text,
            "stt_ms": stt_ms,
            "llm_ms": llm_ms,
            "clipboard": clipboard_backends,
            "typed": typed_successfully,
            "duration": duration,
        }
