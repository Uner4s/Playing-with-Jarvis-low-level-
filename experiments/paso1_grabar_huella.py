#!/usr/bin/env python3
"""
PASO 1 — Grabar y ver la huella matemática de una palabra.

Cómo funciona:
  1. Presionás Enter → grabás la palabra (ej: "Jarvis")
  2. El script extrae los MFCCs (huella matemática) con numpy puro
  3. Te muestra los números que representan ese sonido
  4. Grabás de nuevo y compara qué tan similares son

Uso:
    python3 experiments/paso1_grabar_huella.py
"""

import numpy as np
import sounddevice as sd
from scipy.fftpack import dct

SAMPLE_RATE  = 44100
DURACION_SEG = 2
N_MFCC       = 13    # coeficientes estándar
N_FILTROS    = 26    # filtros del banco Mel


# ──────────────────────────────────────────────────────────────────────────────
#  Cálculo de MFCCs sin librosa
# ──────────────────────────────────────────────────────────────────────────────

def hz_a_mel(hz):
    return 2595 * np.log10(1 + hz / 700)

def mel_a_hz(mel):
    return 700 * (10 ** (mel / 2595) - 1)

def banco_filtros_mel(n_filtros, n_fft, sr):
    """Crea un banco de filtros triangulares en escala Mel."""
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

def extraer_mfcc(audio: np.ndarray, sr=SAMPLE_RATE, n_mfcc=N_MFCC) -> np.ndarray:
    """
    Pipeline MFCC manual:
      1. Dividir en frames de 25ms con 50% de overlap
      2. Ventana de Hamming para suavizar bordes
      3. FFT → espectro de potencia
      4. Banco de filtros Mel → comprime frecuencias como el oído humano
      5. Log → imita la percepción logarítmica del volumen
      6. DCT → extrae los coeficientes más representativos
    """
    frame_len    = int(0.025 * sr)   # 25ms
    frame_step   = int(0.010 * sr)   # 10ms de paso
    n_fft        = 512

    # Frames solapados
    n_frames = 1 + (len(audio) - frame_len) // frame_step
    indices  = (np.arange(frame_len)[None, :] +
                np.arange(n_frames)[:, None] * frame_step)
    frames   = audio[indices] * np.hamming(frame_len)

    # Espectro de potencia
    mag   = np.abs(np.fft.rfft(frames, n=n_fft)) ** 2

    # Banco Mel
    filtros = banco_filtros_mel(N_FILTROS, n_fft, sr)
    energia = np.dot(mag, filtros.T)
    energia = np.where(energia == 0, np.finfo(float).eps, energia)

    # Log + DCT
    log_energia = np.log(energia)
    mfcc = dct(log_energia, type=2, axis=1, norm='ortho')[:, :n_mfcc]

    return mfcc.T   # shape: (n_mfcc, n_frames)


# ──────────────────────────────────────────────────────────────────────────────
#  Grabación y visualización
# ──────────────────────────────────────────────────────────────────────────────

def grabar(duracion: int) -> np.ndarray:
    print(f"\n  🔴 Grabando {duracion} segundos... hablá ahora!")
    audio = sd.rec(
        int(duracion * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32"
    )
    sd.wait()
    print("  ⬛ Listo.")
    return audio.flatten()


def recortar_silencio(audio: np.ndarray, umbral=0.01, frame=1024) -> np.ndarray:
    """Elimina los frames silenciosos al inicio y al final."""
    n_frames = len(audio) // frame
    energias = [np.sqrt(np.mean(audio[i*frame:(i+1)*frame]**2)) for i in range(n_frames)]
    activos  = [i for i, e in enumerate(energias) if e > umbral]
    if not activos:
        return audio
    inicio = max(0, activos[0] - 1)
    fin    = min(n_frames, activos[-1] + 2)
    return audio[inicio*frame : fin*frame]


def mostrar_huella(mfcc: np.ndarray, label: str):
    promedio = np.mean(mfcc, axis=1)
    print(f"\n  📊 Huella de '{label}':")
    print(f"     ({mfcc.shape[0]} coeficientes × {mfcc.shape[1]} frames de tiempo)\n")
    print("  Coef | Valor    | Visualización")
    print("  " + "-" * 45)
    for i, val in enumerate(promedio):
        barra = "█" * min(int(abs(val) / 3), 30)
        signo = "+" if val >= 0 else "-"
        print(f"  [{i:02d}] | {val:+7.2f}  | {signo}{barra}")


def distancia(mfcc1, mfcc2) -> float:
    """Distancia euclidiana entre los promedios de dos huellas."""
    return float(np.linalg.norm(np.mean(mfcc1, axis=1) - np.mean(mfcc2, axis=1)))


# ──────────────────────────────────────────────────────────────────────────────
#  Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  🎤  PASO 1 — Huella matemática de tu voz")
    print("=" * 55)
    print("\n  Vamos a grabar dos veces la misma palabra")
    print("  para ver si la huella matemática es similar.\n")

    palabra = input("  ¿Qué palabra vas a usar como trigger? (ej: Jarvis): ").strip() or "Jarvis"

    # Grabación 1
    input(f"\n  [Grabación 1] Enter y decí '{palabra}'...")
    audio1 = recortar_silencio(grabar(DURACION_SEG))
    print(f"     Audio recortado: {len(audio1)/SAMPLE_RATE:.2f}s")
    mfcc1  = extraer_mfcc(audio1)
    mostrar_huella(mfcc1, f"{palabra} — toma 1")

    # Grabación 2
    input(f"\n  [Grabación 2] Enter y decí '{palabra}' de nuevo...")
    audio2 = recortar_silencio(grabar(DURACION_SEG))
    print(f"     Audio recortado: {len(audio2)/SAMPLE_RATE:.2f}s")
    mfcc2  = extraer_mfcc(audio2)
    mostrar_huella(mfcc2, f"{palabra} — toma 2")

    # Resultado
    dist = distancia(mfcc1, mfcc2)
    print("\n" + "=" * 55)
    print(f"  📏 Distancia entre tus dos '{palabra}': {dist:.2f}")
    if dist < 15:
        print("  ✅ Muy similares — huella estable, lista para usar")
    elif dist < 35:
        print("  🟡 Aceptable — funciona pero hay variación natural")
    else:
        print("  ❌ Muy distintas — intentá hablar más parejo")
    print("=" * 55)

    # Guardar template
    np.save("experiments/template_mfcc.npy", mfcc1)
    print(f"\n  💾 Template guardado en experiments/template_mfcc.npy")
    print("  → Lo usamos en el Paso 2 para comparar en tiempo real\n")


if __name__ == "__main__":
    main()
