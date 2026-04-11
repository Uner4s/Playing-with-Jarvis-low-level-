# CLAUDE.md — Jarvis Project

Development context for Claude Code. Read before modifying anything.

---

## What this project is

**Jarvis** is a personal automation system activated by sound, designed to run on macOS. The current script detects two claps via microphone and runs a welcome sequence (voice, music, apps).

The goal is to incrementally add custom features on top of this base: new sound triggers, new actions, external configuration, etc.

---

## Current state

### Main file
- `welcome_jarvis.py` — single script, all logic in one file

### What it does today
1. Continuously listens to the microphone
2. Detects 2 claps within a 2-second window
3. Speaks a welcome message using the system voice
4. Opens YouTube with a fixed URL
5. Opens Claude on screen

### Technical documentation
- `docs/how_it_works.md` — detailed explanation of the audio pipeline, threading, and welcome sequence

---

## Current architecture

```
welcome_jarvis.py
  ├── Configuration (constants at the top)
  ├── audio_callback()    ← sounddevice thread, do not block
  ├── welcome_sequence()  ← daemon thread
  │     ├── speak()
  │     ├── open_youtube()
  │     └── open_apps()
  └── main()              ← main loop
```

Trigger state is global (`triggered`, `clap_times`) protected with `threading.Lock()`.

---

## Current design decisions

- **macOS only:** uses `say`, `open -a`, `osascript`. No cross-platform support yet.
- **Single script:** all logic in one file. When more features are added, modularization will be needed.
- **Config in source:** constants are at the top of the file. The natural next step is moving them to an external config file.
- **No API keys:** TTS uses the system voice (`say -v Monica`), no cloud dependencies.

---

## Key constants that are often adjusted

```python
THRESHOLD      = 0.20    # raise if false positives, lower if not detecting
COOLDOWN       = 0.1     # minimum seconds between two peaks of the same clap
DOUBLE_WINDOW  = 2.0     # time window for the second clap
MESSAGE        = "..."   # text spoken by the voice
YOUTUBE_URL    = "..."   # song to open
NEW_PROJECT    = "..."   # folder opened by Cursor
```

---

## Backlog

Ideas to implement — update this list as we progress:

- [ ] External config file (`config.json` or `config.toml`) to avoid editing source
- [ ] Multiple sound patterns (1 clap, 3 claps, desk knock) → different actions
- [ ] Configurable "actions" system: which apps to open, which URL, which message
- [ ] Debug mode showing real-time RMS to calibrate THRESHOLD
- [ ] CLI flags (`--threshold`, `--config`, `--dry-run`)
- [ ] Modularization: separate audio detection, actions, and config into distinct modules
- [ ] File logging instead of just prints

---

## Conventions

- Keep configuration constants at the top of the file while it remains a single script
- Do not introduce cloud APIs unless necessary (prefer system tools)
- **All code in English:** file names, variables, functions, constants, and in-code comments must always be in English. Project `.md` documentation files are the only exception — they may be written in Spanish.
- **CLAUDE.md must always be in English**, even if the user communicates in Spanish.
- Update this file before adding any new feature
- Technical documentation goes in `docs/`

---

## How to run

```bash
# Install dependencies
pip install sounddevice numpy pyttsx3

# Run
python welcome_jarvis.py
```

Requires microphone permission on macOS (System → Privacy → Microphone → Terminal/iTerm).
