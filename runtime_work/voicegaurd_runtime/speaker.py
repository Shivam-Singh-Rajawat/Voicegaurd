"""In-memory ECAPA enrollment and verification for authorized 16 kHz mono audio."""
import os
from pathlib import Path

import numpy as np


def _unit_embedding(value):
    vector = np.asarray(value, dtype=np.float32).reshape(-1)
    if vector.size != 192 or not np.isfinite(vector).all():
        raise ValueError("Expected a finite 192-dimensional speaker embedding")
    norm = float(np.linalg.norm(vector))
    if not np.isfinite(norm) or norm == 0:
        raise ValueError("Speaker embedding has no usable direction")
    return vector / norm


class SpeakerVerifier:
    def __init__(self, encode, threshold):
        if not np.isfinite(threshold) or not -1 <= threshold <= 1:
            raise ValueError("Invalid calibrated cosine threshold")
        self.encode = encode
        self.threshold = float(threshold)

    @classmethod
    def from_pretrained(cls, assets, cache_directory, threshold):
        import torch
        from speechbrain.inference.speaker import EncoderClassifier

        assets = Path(assets).resolve(strict=True)
        fetch_options = {}
        if os.name == "nt":
            from speechbrain.utils.fetching import LocalStrategy

            fetch_options["local_strategy"] = LocalStrategy.COPY
        encoder = EncoderClassifier.from_hparams(
            source=str(assets), savedir=str(cache_directory),
            overrides={"pretrained_path": str(assets)}, run_opts={"device": "cpu"},
            **fetch_options,
        )

        def encode(audio):
            with torch.inference_mode():
                return encoder.encode_batch(torch.from_numpy(audio).unsqueeze(0)).cpu().numpy()

        return cls(encode, threshold)

    def embedding(self, samples):
        audio = np.asarray(samples, dtype=np.float32)
        if audio.ndim != 1 or not audio.size or not np.isfinite(audio).all():
            raise ValueError("Expected nonempty, finite mono samples")
        audio = audio[:96000]
        if not np.any(audio):
            raise ValueError("Speaker audio is silent")
        return _unit_embedding(self.encode(audio.copy()))

    def enroll(self, references):
        vectors = [self.embedding(samples) for samples in references]
        if not vectors:
            raise ValueError("Enrollment needs authorized reference audio")
        return _unit_embedding(np.mean(vectors, axis=0))

    def verify(self, samples, template):
        cosine = float(np.clip(self.embedding(samples) @ _unit_embedding(template), -1, 1))
        return {"similarity": cosine, "matched": cosine > self.threshold,
                "threshold": self.threshold, "score_type": "cosine_similarity"}
