#!/usr/bin/env python3
"""
PASO 3 — Trigger por frases de voz con Whisper.

Escucha el micrófono, transcribe lo que decís y busca frases clave.
Cada frase dispara una respuesta distinta.

Uso:
    python3 experiments/paso3_voz_trigger.py

Nota: la primera vez descarga el modelo (~74MB), después queda en caché.
"""

import numpy as np
import sounddevice as sd
import subprocess
import threading
import time
from faster_whisper import WhisperModel

SAMPLE_RATE      = 44100
VOICE_THRESHOLD  = 0.01   # RMS mínimo para detectar voz
SILENCE_FRAMES   = 25     # frames de silencio para cortar la grabación
MAX_FRAMES       = 200    # máximo de frames (~4 seg)

# ──────────────────────────────────────────────────────────────────────────────
#  Frases trigger → respuesta
#  Cada entrada: (palabras_clave, respuesta)
#  Se activa si TODAS las palabras clave aparecen en lo transcripto.
# ──────────────────────────────────────────────────────────────────────────────
TRIGGERS = [
    (["hola", "jarvis"],       "Hola señor Nicolás, ¿en qué le puedo ayudar?"),
    (["hora", "trabajar"],     "Claro, abriendo su entorno de trabajo."),
    (["estás", "despierto"],   "Siempre despierto, señor Nicolás."),
    (["jarvis"],               "Dígame, señor Nicolás."),
]


# ──────────────────────────────────────────────────────────────────────────────
#  TTS — misma función que el script principal
# ──────────────────────────────────────────────────────────────────────────────
def hablar(texto: str):
    print(f"  🔊  {texto}")
    subprocess.run(["say", "-v", "Mónica", texto], capture_output=True)


# ──────────────────────────────────────────────────────────────────────────────
#  Matching de frases
# ──────────────────────────────────────────────────────────────────────────────
def buscar_trigger(texto: str) -> str | None:
    """Busca el primer trigger cuyas palabras clave aparecen en el texto."""
    texto_lower = texto.lower().strip()
    for palabras_clave, respuesta in TRIGGERS:
        if all(p in texto_lower for p in palabras_clave):
            return respuesta
    return None


# ──────────────────────────────────────────────────────────────────────────────
#  Procesamiento de audio capturado
# ──────────────────────────────────────────────────────────────────────────────
def procesar_audio(audio: np.ndarray, modelo: WhisperModel):
    segments, info = modelo.transcribe(
        audio,
        language="es",
        beam_size=1,         # más rápido, suficiente para frases cortas
        vad_filter=True,     # filtra silencio internamente
    )
    texto = " ".join(s.text for s in segments).strip()

    if not texto:
        print("  (no se entendió nada)\n")
        return

    print(f"  📝 Escuché: \"{texto}\"")

    respuesta = buscar_trigger(texto)
    if respuesta:
        print(f"  ✅ Trigger detectado!")
        hablar(respuesta)
    else:
        print(f"  — No es un trigger.\n")

    print("  👂 Escuchando...\n")


# ──────────────────────────────────────────────────────────────────────────────
#  Captura de audio en tiempo real
# ──────────────────────────────────────────────────────────────────────────────
buffer          = []
grabando        = False
frames_silencio = 0
procesando      = False
lock            = threading.Lock()
modelo_global   = None


def audio_callback(indata, frames, time_info, status):
    global buffer, grabando, frames_silencio, procesando

    if procesando:
        return

    audio = indata.flatten()
    rms   = float(np.sqrt(np.mean(audio ** 2)))

    with lock:
        if not grabando:
            if rms > VOICE_THRESHOLD:
                grabando = True
                frames_silencio = 0
                buffer = [audio]
                print("  🔴 Grabando...", end="", flush=True)
        else:
            buffer.append(audio)
            print(".", end="", flush=True)

            frames_silencio = frames_silencio + 1 if rms < VOICE_THRESHOLD else 0

            if frames_silencio >= SILENCE_FRAMES or len(buffer) >= MAX_FRAMES:
                grabando   = False
                procesando = True
                audio_completo = np.concatenate(buffer).astype(np.float32)
                buffer = []
                print()
                threading.Thread(
                    target=run_procesamiento,
                    args=(audio_completo,),
                    daemon=True
                ).start()


def run_procesamiento(audio: np.ndarray):
    global procesando
    procesar_audio(audio, modelo_global)
    procesando = False


# ──────────────────────────────────────────────────────────────────────────────
#  Main
# ──────────────────────────────────────────────────────────────────────────────
def main():
    global modelo_global

    print("=" * 55)
    print("  🤖  PASO 3 — Trigger por voz con Whisper")
    print("=" * 55)
    print("\n  Cargando modelo... (primera vez descarga ~74MB)\n")

    modelo_global = WhisperModel("base", device="cpu", compute_type="int8")
    print("  ✅ Modelo listo.\n")

    print("  Frases que reconozco:")
    for palabras, respuesta in TRIGGERS:
        print(f"    • \"{' '.join(palabras)}\" → {respuesta}")

    print("\n  Ctrl+C para salir.\n")
    print("  👂 Escuchando...\n")

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
        print("\n\nHasta luego! 👋")


if __name__ == "__main__":
    main()
