# 🎙️ Vocalis

> **A Wispr Flow–inspired, ultra-fast AI voice dictation and code formatting CLI for developers, powered by Groq & `uv`.**

Vocalis brings the magic of modern voice dictation into your terminal and editor. Speak naturally—mumbling, hesitating, or dictating code—and Vocalis transcribes your voice in **~200ms** via Groq Whisper, removes all filler words (*"um"*, *"ah"*, *"like"*), formats your speech into clean prose or syntax-highlighted code with Llama 3.3, and copies it straight to your clipboard using **OSC 52** and native system clipboards.

---

## ✨ Features

- **⚡ Sub-Second Latency**: Powered by Groq's high-speed Whisper (`whisper-large-v3-turbo`) and `openai/gpt-oss-120b` (or `llama-3.3-70b-versatile`).
- **🧠 Wispr Flow AI Refinement**: Automatically cleans disfluencies, false starts, and repetitions while preserving your exact intent.
- **🎯 4 Tailored Modes**:
  - `prose` (Default): Clean, professional prose for comments, docs, commit messages, and emails.
  - `code`: Understands programming idioms (`camelCase`, `snake_case`, functions, indentation, syntax).
  - `prompt`: Transforms spoken brainstorming into structured prompts for AI assistants (Cursor, Claude, Copilot).
  - `raw`: Verbatim Whisper transcription without LLM post-processing.
- **🎙️ Zero-Lag Voice Activity Detection (VAD)**: Dynamic noise-floor calibration detects when you start and stop speaking automatically.
- **📋 Universal Clipboard Injection**: Supports **OSC 52** (works natively inside VS Code, Cursor, Neovim, tmux, Alacritty, Kitty, WezTerm) alongside Wayland (`wl-copy`) and X11 (`xclip`).
- **📦 Managed with `uv`**: Ultra-fast packaging, deterministic virtualenvs, and simple execution.

---

## 🚀 Quick Start

### 1. Installation

Clone and sync the project with [`uv`](https://github.com/astral-sh/uv):

```bash
cd vocalis
uv sync
```

To run `vocalis` from anywhere, add an alias to your shell profile (`~/.bashrc` or `~/.zshrc`):

```bash
alias vocalis="uv run --directory /home/ishan/vocalis vocalis"
```

Or install it globally using `uv tool`:

```bash
uv tool install .
```

---

### 2. Configure Your Groq API Key

Set your Groq key via the CLI (saved in `~/.config/vocalis/config.json`):

```bash
vocalis config set groq_api_key gsk_YOUR_GROQ_API_KEY
```

Or export the standard environment variable:

```bash
export GROQ_API_KEY="gsk_YOUR_GROQ_API_KEY"
```

---

### 3. Test Your Microphone

Run the live visual VU meter to verify your audio input:

```bash
vocalis test-mic
```

---

## 💻 Usage

### Basic Dictation
Start listening in your terminal or editor split:

```bash
vocalis start
```

Speak your thoughts naturally. When you finish speaking, Vocalis automatically detects silence, processes the audio through Groq, prints the result card, and copies the refined text to your clipboard.

### One-Shot Mode (Best for Editor Keybindings)
Record a single thought, copy to clipboard, and exit:

```bash
vocalis start --once
```

### Dictate Code
Converts verbal programming into clean syntax:

```bash
vocalis start --mode code
```
> **You say:** *"Make an async function called fetch user that takes user id as an int and returns a dictionary"*  
> **Vocalis writes:** `async def fetch_user(user_id: int) -> dict:`

### Dictate Prompts for AI Coding Assistants
Converts rambling ideas into structured prompts:

```bash
vocalis start --mode prompt
```

### Continuous Loop
Keep listening for multiple thoughts:

```bash
vocalis start --continuous
```

### Manual Push-to-Talk
Ignore silence detection and press **Enter** when you're done speaking:

```bash
vocalis start --manual
```

### Quiet / Direct Pipe Mode
Output only the final text to stdout (ideal for shell piping):

```bash
vocalis start --once --quiet > draft.txt
```

---

## 🛠️ Editor Integration

Run `vocalis setup-editor` to view configuration snippets for your editor:

### VS Code / Cursor Integration

1. In `.vscode/tasks.json` (or User Tasks `Ctrl+Shift+P` → `Tasks: Open User Tasks`):
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

2. In `keybindings.json` (`Ctrl+Shift+P` → `Preferences: Open Keyboard Shortcuts (JSON)`):
```json
[
  {
    "key": "ctrl+alt+v",
    "command": "workbench.action.tasks.runTask",
    "args": "Vocalis: Dictate"
  }
]
```

Now pressing `Ctrl+Alt+V` in VS Code starts listening, and the moment you pause, the result is in your clipboard ready to paste!


## ⚙️ Configuration Reference

Inspect your current configuration:

```bash
vocalis config show
```

Update any setting with `vocalis config set <key> <value>`:

| Key | Default | Description |
| :--- | :--- | :--- |
| `groq_api_key` | `None` | Your Groq API key |
| `default_mode` | `prose` | Default mode: `prose`, `code`, `prompt`, `raw` |
| `stt_model` | `whisper-large-v3-turbo` | Groq Whisper model |
| `llm_model` | `openai/gpt-oss-120b` | Groq LLM model (`openai/gpt-oss-120b`, `llama-3.3-70b-versatile`, etc.) |
| `silence_duration` | `0.9` | Seconds of silence before auto-finishing recording |
| `energy_threshold` | `0.012` | Voice activity detection RMS threshold |
| `language` | `en` | Speech language code (`en`, `es`, `fr`, or `auto`) |
| `auto_copy` | `True` | Automatically copy output to clipboard |
| `input_device` | `None` | Audio input device (run `vocalis list-devices`) |

---

## 🧪 Testing

Run the test suite with `uv`:

```bash
uv run pytest
```
