# How Jarvis Works

Technical documentation for the `bienvenido_jarvis.py` script.

---

## Overview

The script continuously listens to the microphone on a dedicated audio thread. When it detects two claps within a time window, it triggers a welcome sequence: plays a voice message, opens YouTube, and arranges two apps on screen.

```
Microphone
   │
   ▼
audio_callback()   ← sounddevice thread (real-time)
   │
   ├── measures RMS of audio block
   ├── compares against THRESHOLD
   ├── records clap timestamp
   └── if count >= 2 → fires secuencia_bienvenida() in a new thread
                              │
                              ├── hablar()
                              ├── abrir_youtube()
                              └── abrir_apps_lado_a_lado()
```

---

## Audio detection pipeline

### 1. Audio capture (`sounddevice.InputStream`)

- **Sample rate:** 44100 Hz (CD quality)
- **Block size:** 2205 samples = 50 ms per block
- The stream calls `audio_callback()` every 50 ms with a fresh audio block

### 2. RMS calculation

```python
rms = float(np.sqrt(np.mean(indata ** 2)))
```

RMS (Root Mean Square) measures the sound energy of the block. A clap generates an energy spike well above ambient noise. The value is normalized in the range `[0.0, 1.0]`.

### 3. Double-clap logic

```
rms > THRESHOLD
       │
       ├── last clap was less than COOLDOWN ago? → ignore (same clap)
       │
       └── record timestamp
               │
               └── discard claps outside DOUBLE_WINDOW
                       │
                       └── count >= 2? → TRIGGER
```

| Constant        | Default value | Effect |
|----------------|--------------|--------|
| `THRESHOLD`    | `0.20`       | Sensitivity: raise to reduce false positives, lower if not detecting |
| `COOLDOWN`     | `0.1 s`      | Prevents a single clap from counting twice |
| `DOUBLE_WINDOW`| `2.0 s`      | Maximum time between first and second clap |

### 4. Concurrency and thread safety

- `audio_callback` runs on the sounddevice thread (real-time, do not block)
- Shared state (`clap_times`, `triggered`) is protected with `threading.Lock()`
- The welcome sequence runs in a separate daemon thread so it doesn't block listening
- `triggered = True` during the sequence prevents re-triggering; reset to `False` after 8 s in the main thread

---

## Welcome sequence

### `hablar(texto)`

1. Tries `say -v Monica <texto>` (Spanish macOS voice, high quality, no API key)
2. If it fails (Monica not available), falls back to `pyttsx3`:
   - Searches for voices with `"es"` in the ID or `"spanish"` in the name
   - Falls back to the default voice if no Spanish voice is found

### `abrir_youtube()`

Opens `YOUTUBE_URL` with `webbrowser.open()` (uses the system's default browser).

### `abrir_apps_lado_a_lado()`

1. Gets screen resolution via AppleScript + Finder
2. Opens the Claude app with `open -a Claude`
3. Searches for the Cursor CLI in known paths and opens it with `NEW_PROJECT`
4. Uses AppleScript to position the windows:
   - Claude: left half `(0, 0, half, height)`
   - Cursor: right half `(half, 0, half, height)`

---

## Main thread flow (`main`)

```
main()
  └── sd.InputStream (active)
        └── loop: sleep 0.1s
              └── if triggered:
                    sleep 8s  ← waits for sequence to finish
                    triggered = False
                    back to listening
```

---

## Configuration constants

All located at the top of the file for easy tuning without touching the logic:

```python
SAMPLE_RATE    = 44100          # audio capture rate in Hz
BLOCK_SIZE     = int(44100 * 0.05)  # samples per block (50 ms)
THRESHOLD      = 0.20           # minimum energy to detect a clap
COOLDOWN       = 0.1            # minimum seconds between claps
DOUBLE_WINDOW  = 2.0            # window to count 2 claps

YOUTUBE_URL    = "..."          # URL to open
MENSAJE        = "..."          # text spoken by the voice
NEW_PROJECT    = "..."          # folder opened in Cursor
```

---

## Dependencies

| Package       | Use |
|--------------|-----|
| `sounddevice` | Microphone audio capture |
| `numpy`       | RMS calculation on the buffer |
| `pyttsx3`     | TTS fallback if `say` fails |
| `subprocess`  | `say`, `open`, `osascript`, `cursor` |
| `webbrowser`  | Open YouTube in the default browser |
| `threading`   | Thread for the sequence + Lock for shared state |

---

## Known limitations

- **macOS only:** uses `say`, `open -a`, `osascript`, Finder
- **Hardcoded apps:** specifically opens Claude and Cursor
- **Hardcoded reset time:** fixed 8 s in `main()`, does not wait for the actual thread
- **Short `COOLDOWN`:** 100 ms may be insufficient for very loud claps that generate echo
- **No external config:** everything is configured by editing the source directly
