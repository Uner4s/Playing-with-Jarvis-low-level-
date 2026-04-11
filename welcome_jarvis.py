#!/usr/bin/env python3
"""
Double-clap welcome script — Jarvis.

Detects 2 claps → voice says welcome → opens YouTube → opens Claude.

Dependencies:
    pip install sounddevice numpy pyttsx3

Usage:
    python welcome_jarvis.py
"""

import os
import sys
import time
import threading
import subprocess
import webbrowser

import numpy as np
import sounddevice as sd
import pyttsx3

# ──────────────────────────────────────────────────────────────────────────────
#  Configuration
# ──────────────────────────────────────────────────────────────────────────────
SAMPLE_RATE    = 44100
THRESHOLD      = 0.15     # minimum RMS to count as a clap  ← adjust if needed
COOLDOWN       = 0.1      # minimum pause in seconds between claps
DOUBLE_WINDOW  = 3.0      # time window for the second clap

DEBUG          = False    # set to True to calibrate THRESHOLD

YOUTUBE_URL    = "https://www.youtube.com/watch?v=hEIexwwiKKU"
MESSAGE        = "Bienvenido a casa, señor Nicolás."

# ──────────────────────────────────────────────────────────────────────────────
#  Global state
# ──────────────────────────────────────────────────────────────────────────────
clap_times: list[float] = []
triggered = False
lock = threading.Lock()


# ──────────────────────────────────────────────────────────────────────────────
#  Clap detection
# ──────────────────────────────────────────────────────────────────────────────
def audio_callback(indata, frames, time_info, status):
    global triggered, clap_times

    if triggered:
        return

    rms = float(np.sqrt(np.mean(indata ** 2)))
    now = time.time()

    if DEBUG and rms > 0.01:
        print(f"  sound: {rms:.4f}", flush=True)

    if rms > THRESHOLD:
        with lock:
            # Skip if we're in the cooldown period of the previous clap
            if clap_times and (now - clap_times[-1]) < COOLDOWN:
                return

            clap_times.append(now)
            # Remove claps outside the window
            clap_times = [t for t in clap_times if now - t <= DOUBLE_WINDOW]

            count = len(clap_times)
            print(f"  👏  Clap {count}/2  (RMS={rms:.3f})")

            if count >= 2:
                triggered = True
                clap_times = []
                threading.Thread(target=welcome_sequence, daemon=True).start()


# ──────────────────────────────────────────────────────────────────────────────
#  Welcome sequence
# ──────────────────────────────────────────────────────────────────────────────
def welcome_sequence():
    print("\n🚀  Starting welcome sequence…\n")

    speak(MESSAGE)
    open_youtube()
    open_apps()

    print("\n✅  Sequence complete.\n")


def speak(text: str):
    """Local TTS with pyttsx3 (uses system voices, no API key)."""
    print(f"  🔊  Speaking: «{text}»")

    # First try macOS 'say' command (better quality)
    result = subprocess.run(
        ["say", "-v", "Mónica", text],
        capture_output=True
    )
    if result.returncode == 0:
        return  # success with Monica (Spanish macOS voice)

    # Fallback: pyttsx3
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")

    # Look for a Spanish voice
    esp = [v for v in voices if "es" in v.id.lower() or "spanish" in v.name.lower()]
    if esp:
        engine.setProperty("voice", esp[0].id)
        print(f"     Selected voice: {esp[0].name}")
    else:
        print("     Using default voice (no Spanish voice found)")

    engine.setProperty("rate", 148)
    engine.say(text)
    engine.runAndWait()


def open_youtube():
    print(f"  🎵  Opening YouTube…")
    webbrowser.open(YOUTUBE_URL)
    time.sleep(1.2)  # let the browser load before continuing


def open_apps():
    # ── Open Claude ──────────────────────────────────────────────────────────
    print("  🤖  Opening Claude…")
    subprocess.Popen(["open", "-a", "Claude"])


# ──────────────────────────────────────────────────────────────────────────────
#  Main
# ──────────────────────────────────────────────────────────────────────────────
def main():
    global triggered

    print("=" * 55)
    print("  🎤  Listening for claps… (Ctrl+C to exit)")
    print(f"  Current threshold: {THRESHOLD}  (adjust THRESHOLD if needed)")
    print("=" * 55)

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            callback=audio_callback,
        ):
            while True:
                time.sleep(0.1)
                if triggered:
                    # Wait for the sequence to finish and listen again
                    time.sleep(8)
                    triggered = False
                    print("\n👂  Listening again…\n")
    except KeyboardInterrupt:
        print("\n\nGoodbye! 👋")
        sys.exit(0)


if __name__ == "__main__":
    main()
