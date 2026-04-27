"""
Mel spectrogram song change detector.

Monitors AAC segments as they appear, decodes them with FFmpeg, computes a
mel spectrogram fingerprint, and detects song transitions by measuring
spectral distance between consecutive analysis windows.

When a transition is detected, writes an ISO timestamp to /data/mel_trigger
which the scraper_engine reads and uses to trigger metadata scraping.

Memory-efficient:
  - Processes one segment at a time (6s audio ~ 260KB raw PCM at 22050 Hz mono)
  - Uses only numpy + scipy (no librosa — saves ~200MB)
  - Rolling buffer of 2 fingerprints (current + previous)
  - No FFT caching or large intermediate arrays

Runs as a background process.
"""

import os
import struct
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import posthog_reporter

SEGMENTS_DIR = Path("/data/hls/aac")
MEL_TRIGGER = Path("/data/mel_trigger")
SAMPLE_RATE = 22050
N_FFT = 2048
HOP_LENGTH = 512
N_MELS = 64
# Cosine distance threshold for song change detection.
# Values below this = same song, above = likely song change.
# Tuned for radio audio: speech/jingle transitions are typically > 0.4
CHANGE_THRESHOLD = float(os.environ.get("MEL_CHANGE_THRESHOLD", "0.35"))
# Minimum seconds between reported transitions (debounce)
MIN_TRANSITION_GAP = float(os.environ.get("MEL_MIN_GAP", "10"))

_processed: set[str] = set()
_prev_fingerprint: np.ndarray | None = None
_last_transition_time: float = 0

# Pre-compute mel filterbank (constant, computed once)
_mel_filterbank: np.ndarray | None = None


def _get_mel_filterbank() -> np.ndarray:
    """Create a mel-scale filterbank matrix. Computed once and cached."""
    global _mel_filterbank
    if _mel_filterbank is not None:
        return _mel_filterbank

    # Mel scale conversion
    low_freq = 0.0
    high_freq = SAMPLE_RATE / 2.0
    low_mel = 2595.0 * np.log10(1.0 + low_freq / 700.0)
    high_mel = 2595.0 * np.log10(1.0 + high_freq / 700.0)
    mel_points = np.linspace(low_mel, high_mel, N_MELS + 2)
    hz_points = 700.0 * (10.0 ** (mel_points / 2595.0) - 1.0)
    bin_points = np.floor((N_FFT + 1) * hz_points / SAMPLE_RATE).astype(int)

    n_fft_bins = N_FFT // 2 + 1
    filterbank = np.zeros((N_MELS, n_fft_bins), dtype=np.float32)
    for i in range(N_MELS):
        left = bin_points[i]
        center = bin_points[i + 1]
        right = bin_points[i + 2]
        for j in range(left, center):
            if center > left:
                filterbank[i, j] = (j - left) / (center - left)
        for j in range(center, right):
            if right > center:
                filterbank[i, j] = (right - j) / (right - center)

    _mel_filterbank = filterbank
    return filterbank


def _decode_segment(path: str) -> np.ndarray | None:
    """Decode a .ts segment to raw PCM using FFmpeg. Returns mono float32 samples."""
    try:
        proc = subprocess.run(
            [
                "ffmpeg", "-v", "error",
                "-i", path,
                "-ac", "1",
                "-ar", str(SAMPLE_RATE),
                "-f", "s16le",
                "-acodec", "pcm_s16le",
                "pipe:1",
            ],
            capture_output=True,
            timeout=10,
        )
        if proc.returncode != 0 or not proc.stdout:
            return None
        # Convert s16le to float32 (memory efficient: convert in place)
        samples = np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32)
        samples /= 32768.0
        return samples
    except (subprocess.TimeoutExpired, Exception) as e:
        print(f"mel: decode error {path}: {e}", flush=True)
        return None


def _compute_fingerprint(samples: np.ndarray) -> np.ndarray:
    """Compute a compact mel spectrogram fingerprint from audio samples.

    Returns the mean mel energy across time as a 1D vector of N_MELS floats.
    This is enough for transition detection without storing full spectrograms.
    """
    filterbank = _get_mel_filterbank()
    n_frames = max(1, (len(samples) - N_FFT) // HOP_LENGTH + 1)

    # Compute STFT magnitude in chunks to save memory
    mel_sum = np.zeros(N_MELS, dtype=np.float64)
    window = np.hanning(N_FFT).astype(np.float32)

    for i in range(n_frames):
        start = i * HOP_LENGTH
        frame = samples[start:start + N_FFT]
        if len(frame) < N_FFT:
            break
        windowed = frame * window
        spectrum = np.abs(np.fft.rfft(windowed))
        mel_energies = filterbank @ spectrum
        mel_sum += mel_energies

    # Mean across time, log scale
    mel_mean = mel_sum / max(n_frames, 1)
    mel_mean = np.log1p(mel_mean)  # log(1 + x) to avoid log(0)

    # Normalize to unit vector for cosine distance
    norm = np.linalg.norm(mel_mean)
    if norm > 0:
        mel_mean /= norm

    return mel_mean.astype(np.float32)


def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine distance between two unit vectors."""
    return float(1.0 - np.dot(a, b))


def _process_segment(path: str) -> bool:
    """Process a single segment. Returns True if a song transition is detected."""
    global _prev_fingerprint, _last_transition_time

    samples = _decode_segment(path)
    if samples is None or len(samples) < N_FFT:
        return False

    fingerprint = _compute_fingerprint(samples)
    # Free samples immediately
    del samples

    if _prev_fingerprint is None:
        _prev_fingerprint = fingerprint
        return False

    distance = _cosine_distance(_prev_fingerprint, fingerprint)
    _prev_fingerprint = fingerprint

    now = time.time()
    if distance > CHANGE_THRESHOLD and (now - _last_transition_time) > MIN_TRANSITION_GAP:
        _last_transition_time = now
        print(f"mel: song transition detected (distance={distance:.3f})", flush=True)
        return True

    return False


def _write_trigger(epoch: float):
    """Write an ISO timestamp to the mel trigger file for the scraper engine."""
    iso = datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()
    MEL_TRIGGER.write_text(iso)


def main():
    global _prev_fingerprint

    print(f"mel: starting analyzer (threshold={CHANGE_THRESHOLD}, min_gap={MIN_TRANSITION_GAP}s)", flush=True)

    # Wait for segments directory to exist
    while not SEGMENTS_DIR.exists():
        time.sleep(2)

    while True:
        try:
            # Find new .ts segments
            current_files = set()
            for name in os.listdir(SEGMENTS_DIR):
                if name.endswith(".ts"):
                    current_files.add(name)

            new_files = current_files - _processed
            if new_files:
                # Process in chronological order (segment names are epoch timestamps)
                for name in sorted(new_files):
                    path = str(SEGMENTS_DIR / name)
                    if _process_segment(path):
                        # Extract epoch from segment filename
                        try:
                            epoch = float(name.replace(".ts", ""))
                        except ValueError:
                            epoch = time.time()
                        _write_trigger(epoch)
                    _processed.add(name)

                # Prune processed set to avoid memory growth
                if len(_processed) > 500:
                    _processed.intersection_update(current_files)

        except Exception as e:
            print(f"mel: error: {e}", flush=True)

        time.sleep(2)


if __name__ == "__main__":
    posthog_reporter.install_global_handler("mel_analyzer")
    main()
