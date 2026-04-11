#!/usr/bin/env python3
"""
STEP 2 — Real-time comparison against the saved template.

How it works:
  1. Loads the MFCC template from Step 1
  2. Continuously listens to the microphone
  3. When it detects voice, captures the audio
  4. Extracts MFCCs and compares them against the template
  5. Shows the distance and whether it's a MATCH or not

Usage:
    python3 experiments/step2_compare.py
"""

import numpy as np
import sounddevice as sd
from scipy.fftpack import dct
import time
import threading

SAMPLE_RATE      = 44100
VOICE_THRESHOLD  = 0.01    # minimum RMS to consider voice present
SILENCE_FRAMES   = 20      # silence frames to consider recording done
MAX_FRAMES       = 150     # maximum frames to capture (~3 sec)
MATCH_DISTANCE   = 35      # maximum distance to consider a MATCH ← adjust based on results


# ──────────────────────────────────────────────────────────────────────────────
#  MFCCs (same code as Step 1)
# ──────────────────────────────────────────────────────────────────────────────

def hz_to_mel(hz):
    return 2595 * np.log10(1 + hz / 700)

def mel_to_hz(mel):
    return 700 * (10 ** (mel / 2595) - 1)

def mel_filter_bank(n_filters, n_fft, sr):
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

def extract_mfcc(audio: np.ndarray, sr=SAMPLE_RATE, n_mfcc=13) -> np.ndarray:
    frame_len  = int(0.025 * sr)
    frame_step = int(0.010 * sr)
    n_fft      = 512
    n_filters  = 26

    if len(audio) < frame_len:
        return None

    n_frames = 1 + (len(audio) - frame_len) // frame_step
    indices  = (np.arange(frame_len)[None, :] +
                np.arange(n_frames)[:, None] * frame_step)
    frames   = audio[indices] * np.hamming(frame_len)

    mag     = np.abs(np.fft.rfft(frames, n=n_fft)) ** 2
    filters = mel_filter_bank(n_filters, n_fft, sr)
    energy  = np.dot(mag, filters.T)
    energy  = np.where(energy == 0, np.finfo(float).eps, energy)

    log_energy = np.log(energy)
    mfcc = dct(log_energy, type=2, axis=1, norm='ortho')[:, :n_mfcc]
    return mfcc.T


def distance(mfcc1, mfcc2) -> float:
    return float(np.linalg.norm(np.mean(mfcc1, axis=1) - np.mean(mfcc2, axis=1)))


# ──────────────────────────────────────────────────────────────────────────────
#  Real-time detector
# ──────────────────────────────────────────────────────────────────────────────

buffer         = []
recording      = False
silence_frames = 0
lock           = threading.Lock()
template_mfcc  = None


def compare_against_template(audio: np.ndarray):
    mfcc = extract_mfcc(audio)
    if mfcc is None:
        return

    dist     = distance(template_mfcc, mfcc)
    is_match = dist < MATCH_DISTANCE

    if is_match:
        print(f"\n  ✅ MATCH  — distance: {dist:.1f}  (threshold: {MATCH_DISTANCE})")
    else:
        print(f"\n  ❌ No match — distance: {dist:.1f}  (threshold: {MATCH_DISTANCE})")

    print("  👂 Listening...\n")


def audio_callback(indata, frames, time_info, status):
    global buffer, recording, silence_frames

    audio = indata.flatten()
    rms   = float(np.sqrt(np.mean(audio ** 2)))

    with lock:
        if not recording:
            if rms > VOICE_THRESHOLD:
                recording      = True
                silence_frames = 0
                buffer         = [audio]
                print("  🔴 Capturing...", end="", flush=True)
        else:
            buffer.append(audio)
            print(".", end="", flush=True)

            if rms < VOICE_THRESHOLD:
                silence_frames += 1
            else:
                silence_frames = 0

            if silence_frames >= SILENCE_FRAMES or len(buffer) >= MAX_FRAMES:
                recording  = False
                full_audio = np.concatenate(buffer)
                buffer     = []
                threading.Thread(
                    target=compare_against_template,
                    args=(full_audio,),
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
        print("  ❌ experiments/template_mfcc.npy not found")
        print("     Run first: python3 experiments/step1_record_fingerprint.py")
        return

    print("=" * 55)
    print("  🎤  STEP 2 — Real-time comparison")
    print(f"  Template loaded: {template_mfcc.shape}")
    print(f"  Match threshold: distance < {MATCH_DISTANCE}")
    print("=" * 55)
    print("\n  Say your trigger word and check the distance.")
    print("  If values are consistent, adjust MATCH_DISTANCE.")
    print("  Ctrl+C to exit.\n")
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
