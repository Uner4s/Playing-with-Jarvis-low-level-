# Jarvis - Audio Automation

A personal automation system triggered by sound, running fully local on macOS.

## Current state

The working trigger today is a **double clap**: two claps detected by the microphone activate a welcome sequence — voice, music, and apps.

But that's just the starting point.

## The real goal

The goal is to build a **signal-math-based audio recognition system**, without relying on external integrations or pre-trained ML models. The idea is to understand and control every layer of the pipeline:

```
Microphone → raw audio signal
    → mathematical analysis (RMS, FFT, MFCCs)
    → sound fingerprint comparison
    → voice-specific trigger
    → action
```

Have Jarvis understand "hey Jarvis" or "time to work" not because we gave it a model trained by someone else, but because we built the logic that compares sound mathematically.

## What exists today

| File | What it does |
|---|---|
| `bienvenido_jarvis.py` | Main script — double clap → welcome + YouTube + Claude |
| `experiments/paso1_grabar_huella.py` | Records a word and extracts its MFCC fingerprint with pure numpy |
| `experiments/paso2_comparar.py` | Compares incoming real-time audio against a saved template |
| `experiments/paso3_voz_trigger.py` | Phrase trigger using Whisper as a reference experiment |
| `docs/how_it_works.md` | Technical documentation of the audio pipeline and threading |

## What we learned experimenting

- RMS only detects sound energy — useful for claps, not words
- MFCC averages describe the speaker, not the word — they don't discriminate between phrases
- Silence trimming is critical before comparing fingerprints
- Whisper works well as a reference, but the goal is to not depend on it

## Installation

```bash
pip3 install sounddevice numpy pyttsx3 scipy
```

## Usage

```bash
# Main script (double clap)
python3 bienvenido_jarvis.py

# Audio experiments
python3 experiments/paso1_grabar_huella.py
python3 experiments/paso2_comparar.py
python3 experiments/paso3_voz_trigger.py
```

## Requirements

- macOS (uses `say` for TTS and `osascript` for apps)
- Python 3.9+
- Microphone permissions in Settings → Privacy → Microphone
- iTerm2 or a terminal with microphone access enabled
