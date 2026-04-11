#!/usr/bin/env python3
"""
STEP 3 — Voice phrase trigger with Whisper.

Listens to the microphone, transcribes speech and looks for key phrases.
Each phrase fires a different response.

Usage:
    python3 experiments/step3_voice_trigger.py

Note: first run downloads the model (~74MB), then it's cached.
"""

import numpy as np
import sounddevice as sd
import subprocess
import threading
import time
from faster_whisper import WhisperModel

SAMPLE_RATE      = 44100
VOICE_THRESHOLD  = 0.01   # minimum RMS to detect voice
SILENCE_FRAMES   = 25     # silence frames to cut the recording
MAX_FRAMES       = 200    # maximum frames (~4 sec)

# ──────────────────────────────────────────────────────────────────────────────
#  Voice phrase triggers → response
#  Each entry: (keywords, response)
#  Fires if ALL keywords appear in the transcribed text.
# ──────────────────────────────────────────────────────────────────────────────
TRIGGERS = [
    (["hola", "jarvis"],       "Hola señor Nicolás, ¿en qué le puedo ayudar?"),
    (["hora", "trabajar"],     "Claro, abriendo su entorno de trabajo."),
    (["estás", "despierto"],   "Siempre despierto, señor Nicolás."),
    (["jarvis"],               "Dígame, señor Nicolás."),
]


# ──────────────────────────────────────────────────────────────────────────────
#  TTS — same function as the main script
# ──────────────────────────────────────────────────────────────────────────────
def speak(text: str):
    print(f"  🔊  {text}")
    subprocess.run(["say", "-v", "Mónica", text], capture_output=True)


# ──────────────────────────────────────────────────────────────────────────────
#  Phrase matching
# ──────────────────────────────────────────────────────────────────────────────
def find_trigger(text: str) -> str | None:
    """Finds the first trigger whose keywords all appear in the text."""
    text_lower = text.lower().strip()
    for keywords, response in TRIGGERS:
        if all(p in text_lower for p in keywords):
            return response
    return None


# ──────────────────────────────────────────────────────────────────────────────
#  Processing of captured audio
# ──────────────────────────────────────────────────────────────────────────────
def process_audio(audio: np.ndarray, model: WhisperModel):
    segments, info = model.transcribe(
        audio,
        language="es",
        beam_size=1,         # faster, sufficient for short phrases
        vad_filter=True,     # filters silence internally
    )
    text = " ".join(s.text for s in segments).strip()

    if not text:
        print("  (nothing was understood)\n")
        return

    print(f"  📝 Heard: \"{text}\"")

    response = find_trigger(text)
    if response:
        print(f"  ✅ Trigger detected!")
        speak(response)
    else:
        print(f"  — Not a trigger.\n")

    print("  👂 Listening...\n")


# ──────────────────────────────────────────────────────────────────────────────
#  Real-time audio capture
# ──────────────────────────────────────────────────────────────────────────────
buffer         = []
recording      = False
silence_frames = 0
processing     = False
lock           = threading.Lock()
global_model   = None


def audio_callback(indata, frames, time_info, status):
    global buffer, recording, silence_frames, processing

    if processing:
        return

    audio = indata.flatten()
    rms   = float(np.sqrt(np.mean(audio ** 2)))

    with lock:
        if not recording:
            if rms > VOICE_THRESHOLD:
                recording      = True
                silence_frames = 0
                buffer         = [audio]
                print("  🔴 Recording...", end="", flush=True)
        else:
            buffer.append(audio)
            print(".", end="", flush=True)

            silence_frames = silence_frames + 1 if rms < VOICE_THRESHOLD else 0

            if silence_frames >= SILENCE_FRAMES or len(buffer) >= MAX_FRAMES:
                recording  = False
                processing = True
                full_audio = np.concatenate(buffer).astype(np.float32)
                buffer     = []
                print()
                threading.Thread(
                    target=run_processing,
                    args=(full_audio,),
                    daemon=True
                ).start()


def run_processing(audio: np.ndarray):
    global processing
    process_audio(audio, global_model)
    processing = False


# ──────────────────────────────────────────────────────────────────────────────
#  Main
# ──────────────────────────────────────────────────────────────────────────────
def main():
    global global_model

    print("=" * 55)
    print("  🤖  STEP 3 — Voice phrase trigger with Whisper")
    print("=" * 55)
    print("\n  Loading model... (first run downloads ~74MB)\n")

    global_model = WhisperModel("base", device="cpu", compute_type="int8")
    print("  ✅ Model ready.\n")

    print("  Phrases I recognize:")
    for keywords, response in TRIGGERS:
        print(f"    • \"{' '.join(keywords)}\" → {response}")

    print("\n  Ctrl+C to exit.\n")
    print("  👂 Listening...\n")

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            callback=audio_callback,
        ):
            while True:
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\nGoodbye! 👋")


if __name__ == "__main__":
    main()
