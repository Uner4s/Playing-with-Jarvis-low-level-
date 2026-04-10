#!/usr/bin/env python3
"""
PASO 2 — Comparación en tiempo real contra el template guardado.

Cómo funciona:
  1. Carga el template MFCC del Paso 1
  2. Escucha el micrófono continuamente
  3. Cuando detecta voz, captura el audio
  4. Extrae los MFCCs y los compara contra el template
  5. Muestra la distancia y si es MATCH o no

Uso:
    python3 experiments/paso2_comparar.py
"""

import numpy as np
import sounddevice as sd
from scipy.fftpack import dct
import time
import threading

SAMPLE_RATE      = 44100
VOICE_THRESHOLD  = 0.01    # RMS mínimo para considerar que hay voz
SILENCE_FRAMES   = 20      # frames de silencio para dar la grabación por terminada
MAX_FRAMES       = 150     # máximo de frames a capturar (~3 seg)
MATCH_DISTANCIA  = 35      # distancia máxima para considerar MATCH ← ajustar según resultados


# ──────────────────────────────────────────────────────────────────────────────
#  MFCCs (mismo código del Paso 1)
# ──────────────────────────────────────────────────────────────────────────────

def hz_a_mel(hz):
    return 2595 * np.log10(1 + hz / 700)

def mel_a_hz(mel):
    return 700 * (10 ** (mel / 2595) - 1)

def banco_filtros_mel(n_filtros, n_fft, sr):
    mel_min = hz_a_mel(0)
    mel_max = hz_a_mel(sr / 2)
    puntos_mel = np.linspace(mel_min, mel_max, n_filtros + 2)
    puntos_hz  = mel_a_hz(puntos_mel)
    bins = np.floor((n_fft + 1) * puntos_hz / sr).astype(int)
    filtros = np.zeros((n_filtros, n_fft // 2 + 1))
    for m in range(1, n_filtros + 1):
        f_m_menos = bins[m - 1]
        f_m       = bins[m]
        f_m_mas   = bins[m + 1]
        for k in range(f_m_menos, f_m):
            filtros[m - 1, k] = (k - f_m_menos) / (f_m - f_m_menos)
        for k in range(f_m, f_m_mas):
            filtros[m - 1, k] = (f_m_mas - k) / (f_m_mas - f_m)
    return filtros

def extraer_mfcc(audio: np.ndarray, sr=SAMPLE_RATE, n_mfcc=13) -> np.ndarray:
    frame_len  = int(0.025 * sr)
    frame_step = int(0.010 * sr)
    n_fft      = 512
    n_filtros  = 26

    if len(audio) < frame_len:
        return None

    n_frames = 1 + (len(audio) - frame_len) // frame_step
    indices  = (np.arange(frame_len)[None, :] +
                np.arange(n_frames)[:, None] * frame_step)
    frames   = audio[indices] * np.hamming(frame_len)

    mag     = np.abs(np.fft.rfft(frames, n=n_fft)) ** 2
    filtros = banco_filtros_mel(n_filtros, n_fft, sr)
    energia = np.dot(mag, filtros.T)
    energia = np.where(energia == 0, np.finfo(float).eps, energia)

    log_energia = np.log(energia)
    mfcc = dct(log_energia, type=2, axis=1, norm='ortho')[:, :n_mfcc]
    return mfcc.T


def distancia(mfcc1, mfcc2) -> float:
    return float(np.linalg.norm(np.mean(mfcc1, axis=1) - np.mean(mfcc2, axis=1)))


# ──────────────────────────────────────────────────────────────────────────────
#  Detector en tiempo real
# ──────────────────────────────────────────────────────────────────────────────

buffer        = []
grabando      = False
frames_silencio = 0
lock          = threading.Lock()
template_mfcc = None


def comparar_contra_template(audio: np.ndarray):
    mfcc = extraer_mfcc(audio)
    if mfcc is None:
        return

    dist = distancia(template_mfcc, mfcc)
    es_match = dist < MATCH_DISTANCIA

    if es_match:
        print(f"\n  ✅ MATCH  — distancia: {dist:.1f}  (umbral: {MATCH_DISTANCIA})")
    else:
        print(f"\n  ❌ No match — distancia: {dist:.1f}  (umbral: {MATCH_DISTANCIA})")

    print("  👂 Escuchando...\n")


def audio_callback(indata, frames, time_info, status):
    global buffer, grabando, frames_silencio

    audio = indata.flatten()
    rms   = float(np.sqrt(np.mean(audio ** 2)))

    with lock:
        if not grabando:
            if rms > VOICE_THRESHOLD:
                grabando = True
                frames_silencio = 0
                buffer = [audio]
                print("  🔴 Capturando...", end="", flush=True)
        else:
            buffer.append(audio)
            print(".", end="", flush=True)

            if rms < VOICE_THRESHOLD:
                frames_silencio += 1
            else:
                frames_silencio = 0

            if frames_silencio >= SILENCE_FRAMES or len(buffer) >= MAX_FRAMES:
                grabando = False
                audio_completo = np.concatenate(buffer)
                buffer = []
                threading.Thread(
                    target=comparar_contra_template,
                    args=(audio_completo,),
                    daemon=True
                ).start()


# ──────────────────────────────────────────────────────────────────────────────
#  Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    global template_mfcc

    try:
        template_mfcc = np.load("experiments/template_mfcc.npy")
    except FileNotFoundError:
        print("  ❌ No se encontró experiments/template_mfcc.npy")
        print("     Corré primero: python3 experiments/paso1_grabar_huella.py")
        return

    print("=" * 55)
    print("  🎤  PASO 2 — Comparación en tiempo real")
    print(f"  Template cargado: {template_mfcc.shape}")
    print(f"  Umbral de match:  distancia < {MATCH_DISTANCIA}")
    print("=" * 55)
    print("\n  Decí tu palabra trigger y fijate la distancia.")
    print("  Si los valores son consistentes, ajustamos MATCH_DISTANCIA.")
    print("  Ctrl+C para salir.\n")
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
