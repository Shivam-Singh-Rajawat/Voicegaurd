"""Adapters for preserved research checkpoints; outputs are uncalibrated."""
from pathlib import Path
import threading


def fixed_window(samples, count):
    import numpy as np
    x = np.asarray(samples, dtype=np.float32)
    if x.ndim != 1 or not x.size or not np.isfinite(x).all():
        raise ValueError("Expected nonempty, finite mono samples")
    if count < 1:
        raise ValueError("Window size must be positive")
    if len(x) < count:
        raise ValueError("Audio is shorter than one complete model window")
    start = (len(x) - count) // 2
    return x[start:start + count].copy()


class Detector:
    def __init__(self, checkpoint, device="cpu"):
        import torch
        from voicegaurd_v3.models import load_checkpoint
        if device != "cpu":
            raise ValueError("GPU runtime requires a separately verified allocation")
        self.device = torch.device(device)
        self.checkpoint = str(Path(checkpoint).resolve())
        self.model, payload = load_checkpoint(self.checkpoint, self.device)
        self.seconds = float(payload.get("seconds", 4.0375))
        self.architecture = payload["model_name"]
        self.lock = threading.Lock()

    def score(self, samples):
        import numpy as np
        import torch
        from voicegaurd_v3.score import scores_from_logits
        x = fixed_window(samples, round(self.seconds * 16000))
        # Preserve the existing model loader's amplitude convention.
        wav = torch.from_numpy(np.clip(x, -1, 1)).unsqueeze(0).to(self.device)
        with self.lock, torch.inference_mode():
            value = float(scores_from_logits(self.model(wav))[0].cpu())
        if not np.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("Model returned an invalid score")
        return dict(score=value, calibrated=False, checkpoint=self.checkpoint,
                    architecture=self.architecture, window_seconds=self.seconds)


class VoicegaurdInference:
    def __init__(self, detectors, *, speaker_verifier=None, speaker_template=None):
        if not detectors or set(detectors) - {"synthetic", "replay"}:
            raise ValueError("Configure synthetic and/or replay detectors")
        if (speaker_verifier is None) != (speaker_template is None):
            raise ValueError("Speaker verification requires a verifier and an enrollment template")
        self.detectors = dict(detectors)
        self.speaker_verifier = speaker_verifier
        self.speaker_template = speaker_template
        self.window_seconds = max(model.seconds for model in self.detectors.values())

    def analyze(self, audio_path):
        from .audio import load_audio
        samples, metadata = load_audio(audio_path)
        return dict(audio=metadata, **self.analyze_samples(samples))

    def analyze_samples(self, samples):
        """Analyze mono 16 kHz samples without repeating short recordings."""
        import numpy as np
        samples = np.asarray(samples, dtype=np.float32)
        if samples.ndim != 1 or not samples.size or not np.isfinite(samples).all():
            raise ValueError("Expected nonempty, finite mono samples")

        silent = not np.any(samples)
        evidence = {}
        for name, model in self.detectors.items():
            if silent or samples.size < round(model.seconds * 16000):
                status = "no_signal" if silent else "insufficient_audio"
                evidence[name] = dict(status=status, score=None,
                                      calibrated=False, window_seconds=model.seconds)
            else:
                evidence[name] = model.score(samples)

        speaker = "unavailable"
        if self.speaker_verifier is not None:
            if silent or samples.size < round(self.window_seconds * 16000):
                status = "no_signal" if silent else "insufficient_audio"
                speaker = dict(status=status, similarity=None, matched=None)
            else:
                speaker = self.speaker_verifier.verify(samples, self.speaker_template)
        return dict(evidence=evidence, speaker_verification=speaker)

    def open_stream(self, hop_seconds=1.0):
        from .streaming import InferenceStream
        return InferenceStream(self, self.window_seconds, hop_seconds)
