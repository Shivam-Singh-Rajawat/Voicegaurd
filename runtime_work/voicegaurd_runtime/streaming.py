"""Per-session buffering of already resampled 16 kHz mono audio."""
import numpy as np


class AudioBuffer:
    def __init__(self, window_seconds=4.0375, hop_seconds=1.0, sample_rate=16000):
        if sample_rate != 16000:
            raise ValueError("Resample input to 16000 Hz before buffering")
        if not (np.isfinite(window_seconds) and np.isfinite(hop_seconds)):
            raise ValueError("Window and hop must be finite")
        self.window = round(window_seconds * sample_rate)
        self.hop = round(hop_seconds * sample_rate)
        if not 0 < self.hop <= self.window:
            raise ValueError("Require 0 < hop <= window")
        self.pending = np.empty(0, dtype=np.float32)
        self.offset = 0

    def push(self, samples):
        x = np.asarray(samples, dtype=np.float32)
        if x.ndim != 1 or not np.isfinite(x).all():
            raise ValueError("Expected finite mono samples")
        if x.size > 16000 * 10:
            raise ValueError("Send chunks of at most ten seconds")
        self.pending = np.concatenate((self.pending, x))
        windows = []
        while len(self.pending) >= self.window:
            windows.append(dict(start_seconds=self.offset / 16000,
                                audio=self.pending[:self.window].copy()))
            self.pending = self.pending[self.hop:].copy()
            self.offset += self.hop
        return windows

    def reset(self):
        self.pending = np.empty(0, dtype=np.float32)
        self.offset = 0


class InferenceStream:
    """Emit evidence only for complete 16 kHz mono windows."""

    def __init__(self, inference, window_seconds, hop_seconds):
        self.inference = inference
        self.buffer = AudioBuffer(window_seconds, hop_seconds)

    def push(self, samples):
        return [dict(start_seconds=window["start_seconds"],
                     **self.inference.analyze_samples(window["audio"]))
                for window in self.buffer.push(samples)]

    def reset(self):
        self.buffer.reset()
