#!/usr/bin/env python3
"""
Double-clap welcome script — Jarvis.

Detecta 2 aplausos → voz dice bienvenido → abre YouTube → abre Claude.

Dependencias:
    pip install sounddevice numpy pyttsx3

Uso:
    python bienvenido_jarvis.py
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
#  Configuración
# ──────────────────────────────────────────────────────────────────────────────
SAMPLE_RATE    = 44100
THRESHOLD      = 0.15     # RMS mínimo para contar como aplauso  ← ajusta si falla
COOLDOWN       = 0.1    # segundos de pausa mínima entre aplausos
DOUBLE_WINDOW  = 3.0     # ventana de tiempo para el segundo aplauso

DEBUG          = False    # activar en True para calibrar THRESHOLD

YOUTUBE_URL    = "https://www.youtube.com/watch?v=hEIexwwiKKU"
MENSAJE        = "Bienvenido a casa, señor Nicolás."

# ──────────────────────────────────────────────────────────────────────────────
#  Estado global
# ──────────────────────────────────────────────────────────────────────────────
clap_times: list[float] = []
triggered = False
lock = threading.Lock()


# ──────────────────────────────────────────────────────────────────────────────
#  Detección de aplausos
# ──────────────────────────────────────────────────────────────────────────────
def audio_callback(indata, frames, time_info, status):
    global triggered, clap_times

    if triggered:
        return

    rms = float(np.sqrt(np.mean(indata ** 2)))
    now = time.time()

    if DEBUG and rms > 0.01:
        print(f"  sonido: {rms:.4f}", flush=True)

    if rms > THRESHOLD:
        with lock:
            # Ignora si estamos en el cooldown del aplauso anterior
            if clap_times and (now - clap_times[-1]) < COOLDOWN:
                return

            clap_times.append(now)
            # Limpia aplausos fuera de la ventana
            clap_times = [t for t in clap_times if now - t <= DOUBLE_WINDOW]

            count = len(clap_times)
            print(f"  👏  Aplauso {count}/2  (RMS={rms:.3f})")

            if count >= 2:
                triggered = True
                clap_times = []
                threading.Thread(target=secuencia_bienvenida, daemon=True).start()


# ──────────────────────────────────────────────────────────────────────────────
#  Secuencia de bienvenida
# ──────────────────────────────────────────────────────────────────────────────
def secuencia_bienvenida():
    print("\n🚀  Iniciando secuencia de bienvenida…\n")

    hablar(MENSAJE)
    abrir_youtube()
    abrir_apps()

    print("\n✅  Secuencia completada.\n")


def hablar(texto: str):
    """TTS local con pyttsx3 (usa voces del sistema, sin API key)."""
    print(f"  🔊  Diciendo: «{texto}»")

    # Primero intenta con el comando 'say' de macOS (mejor calidad)
    resultado = subprocess.run(
        ["say", "-v", "Mónica", texto],
        capture_output=True
    )
    if resultado.returncode == 0:
        return  # éxito con Monica (voz española de macOS)

    # Fallback: pyttsx3
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")

    # Busca voz en español
    esp = [v for v in voices if "es" in v.id.lower() or "spanish" in v.name.lower()]
    if esp:
        engine.setProperty("voice", esp[0].id)
        print(f"     Voz seleccionada: {esp[0].name}")
    else:
        print("     Usando voz por defecto (no se encontró voz en español)")

    engine.setProperty("rate", 148)
    engine.say(texto)
    engine.runAndWait()


def abrir_youtube():
    print(f"  🎵  Abriendo YouTube…")
    webbrowser.open(YOUTUBE_URL)
    time.sleep(1.2)  # deja que el navegador cargue antes de seguir


def abrir_apps():
    # ── Abre Claude ──────────────────────────────────────────────────────────
    print("  🤖  Abriendo Claude…")
    subprocess.Popen(["open", "-a", "Claude"])



# ──────────────────────────────────────────────────────────────────────────────
#  Main
# ──────────────────────────────────────────────────────────────────────────────
def main():
    global triggered

    print("=" * 55)
    print("  🎤  Escuchando aplausos… (Ctrl+C para salir)")
    print(f"  Umbral actual: {THRESHOLD}  (ajusta THRESHOLD si falla)")
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
                    # Espera a que la secuencia acabe y vuelve a escuchar
                    time.sleep(8)
                    triggered = False
                    print("\n👂  Escuchando de nuevo…\n")
    except KeyboardInterrupt:
        print("\n\nHasta luego! 👋")
        sys.exit(0)


if __name__ == "__main__":
    main()
