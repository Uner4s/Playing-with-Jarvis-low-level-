#!/usr/bin/env python3
"""
STEP 1 — Record and visualize the mathematical fingerprint of a word.

How it works:
  1. Press Enter → record the word (e.g. "Jarvis")
  2. The script extracts MFCCs (mathematical fingerprint) using pure numpy
  3. Shows the numbers that represent that sound
  4. Records again and compares how similar they are

Usage:
    python3 experiments/step1_record_fingerprint.py
"""

import numpy as np
import sounddevice as sd
from scipy.fftpack import dct

SAMPLE_RATE   = 44100
DURATION_SEC  = 2
N_MFCC        = 13    # standard coefficients
N_FILTERS     = 26    # Mel filter bank size


# ──────────────────────────────────────────────────────────────────────────────
#  MFCC calculation without librosa
# ──────────────────────────────────────────────────────────────────────────────

def hz_to_mel(hz):
    return 2595 * np.log10(1 + hz / 700)

def mel_to_hz(mel):
    return 700 * (10 ** (mel / 2595) - 1)

def mel_filter_bank(n_filters, n_fft, sr):
    """Creates a bank of triangular filters on the Mel scale."""
    mel_min = hz_to_mel(0)
    mel_max = hz_to_mel(sr / 2)
    mel_points = np.linspace(mel_min, mel_max, n_filters + 2)
    hz_points  = mel_to_hz(mel_points)
    bins = np.floor((n_fft + 1) * hz_points / sr).astype(int)

    filters = np.zeros((n_filters, n_fft // 2 + 1))
    for m in range(1, n_filters + 1):
        f_m_minus = bins[m - 1]
        f_m       = bins[m]
        f_m_plus  = bins[m + 1]
        for k in range(f_m_minus, f_m):
            filters[m - 1, k] = (k - f_m_minus) / (f_m - f_m_minus)
        for k in range(f_m, f_m_plus):
            filters[m - 1, k] = (f_m_plus - k) / (f_m_plus - f_m)
    return filters

def extract_mfcc(audio: np.ndarray, sr=SAMPLE_RATE, n_mfcc=N_MFCC) -> np.ndarray:
    """
    Manual MFCC pipeline:
      1. Split into 25ms frames with 50% overlap
      2. Hamming window to smooth edges
      3. FFT → power spectrum
      4. Mel filter bank → compresses frequencies like the human ear
      5. Log → mimics logarithmic perception of volume
      6. DCT → extracts the most representative coefficients
    """
    frame_len    = int(0.025 * sr)   # 25ms
    frame_step   = int(0.010 * sr)   # 10ms step
    n_fft        = 512

    # Overlapping frames
    n_frames = 1 + (len(audio) - frame_len) // frame_step
    indices  = (np.arange(frame_len)[None, :] +
                np.arange(n_frames)[:, None] * frame_step)
    frames   = audio[indices] * np.hamming(frame_len)

    # Power spectrum
    mag   = np.abs(np.fft.rfft(frames, n=n_fft)) ** 2

    # Mel filter bank
    filters = mel_filter_bank(N_FILTERS, n_fft, sr)
    energy  = np.dot(mag, filters.T)
    energy  = np.where(energy == 0, np.finfo(float).eps, energy)

    # Log + DCT
    log_energy = np.log(energy)
    mfcc = dct(log_energy, type=2, axis=1, norm='ortho')[:, :n_mfcc]

    return mfcc.T   # shape: (n_mfcc, n_frames)


# ──────────────────────────────────────────────────────────────────────────────
#  Recording and visualization
# ──────────────────────────────────────────────────────────────────────────────

def record(duration: int) -> np.ndarray:
    print(f"\n  🔴 Recording {duration} seconds... speak now!")
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32"
    )
    sd.wait()
    print("  ⬛ Done.")
    return audio.flatten()


def trim_silence(audio: np.ndarray, threshold=0.01, frame=1024) -> np.ndarray:
    """Removes silent frames from the beginning and end."""
    n_frames      = len(audio) // frame
    energies      = [np.sqrt(np.mean(audio[i*frame:(i+1)*frame]**2)) for i in range(n_frames)]
    active_frames = [i for i, e in enumerate(energies) if e > threshold]
    if not active_frames:
        return audio
    start = max(0, active_frames[0] - 1)
    end   = min(n_frames, active_frames[-1] + 2)
    return audio[start*frame : end*frame]


def show_fingerprint(mfcc: np.ndarray, label: str):
    average = np.mean(mfcc, axis=1)
    print(f"\n  📊 Fingerprint of '{label}':")
    print(f"     ({mfcc.shape[0]} coefficients × {mfcc.shape[1]} time frames)\n")
    print("  Coef | Value    | Visualization")
    print("  " + "-" * 45)
    for i, val in enumerate(average):
        bar  = "█" * min(int(abs(val) / 3), 30)
        sign = "+" if val >= 0 else "-"
        print(f"  [{i:02d}] | {val:+7.2f}  | {sign}{bar}")


def distance(mfcc1, mfcc2) -> float:
    """Euclidean distance between the averages of two fingerprints."""
    return float(np.linalg.norm(np.mean(mfcc1, axis=1) - np.mean(mfcc2, axis=1)))


# ──────────────────────────────────────────────────────────────────────────────
#  Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  🎤  STEP 1 — Mathematical fingerprint of your voice")
    print("=" * 55)
    print("\n  We'll record the same word twice")
    print("  to see if the mathematical fingerprint is similar.\n")

    word = input("  What word will you use as trigger? (e.g. Jarvis): ").strip() or "Jarvis"

    # Recording 1
    input(f"\n  [Recording 1] Press Enter and say '{word}'...")
    audio1 = trim_silence(record(DURATION_SEC))
    print(f"     Trimmed audio: {len(audio1)/SAMPLE_RATE:.2f}s")
    mfcc1  = extract_mfcc(audio1)
    show_fingerprint(mfcc1, f"{word} — take 1")

    # Recording 2
    input(f"\n  [Recording 2] Press Enter and say '{word}' again...")
    audio2 = trim_silence(record(DURATION_SEC))
    print(f"     Trimmed audio: {len(audio2)/SAMPLE_RATE:.2f}s")
    mfcc2  = extract_mfcc(audio2)
    show_fingerprint(mfcc2, f"{word} — take 2")

    # Result
    dist = distance(mfcc1, mfcc2)
    print("\n" + "=" * 55)
    print(f"  📏 Distance between your two '{word}': {dist:.2f}")
    if dist < 15:
        print("  ✅ Very similar — stable fingerprint, ready to use")
    elif dist < 35:
        print("  🟡 Acceptable — works but there's natural variation")
    else:
        print("  ❌ Too different — try speaking more consistently")
    print("=" * 55)

    # Save template
    np.save("experiments/template_mfcc.npy", mfcc1)
    print(f"\n  💾 Template saved in experiments/template_mfcc.npy")
    print("  → Used in Step 2 for real-time comparison\n")


if __name__ == "__main__":
    main()
