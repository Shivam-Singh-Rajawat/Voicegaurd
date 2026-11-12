"""Encode one deterministic shard of the frozen CN-Celeb development manifest."""
import argparse
import csv
import hashlib
from math import gcd
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from voicegaurd_runtime.speaker import SpeakerVerifier


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("audio_root", type=Path)
    parser.add_argument("assets", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("shard", type=int)
    parser.add_argument("shards", type=int)
    args = parser.parse_args()
    if not 0 <= args.shard < args.shards:
        parser.error("shard must be between zero and shards minus one")
    digest = hashlib.sha256(args.manifest.read_bytes()).hexdigest()
    if digest != "effb9f5f8fafd46c042938c1a8e28e2808c1010b615f3be8d5464beb08f7e9fa":
        raise ValueError("Unexpected manifest digest")
    with args.manifest.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 60189 or len({row["path"] for row in rows}) != len(rows):
        raise ValueError("Unexpected manifest coverage")
    args.output.mkdir()
    verifier = SpeakerVerifier.from_pretrained(
        args.assets, args.output / "model", 0.4769288897514343
    )
    indices, vectors = [], []
    with (args.output / "coverage.csv").open("x", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("index", "path", "status", "error"))
        for index in range(args.shard, len(rows), args.shards):
            relative = rows[index]["path"]
            try:
                with sf.SoundFile(str(args.audio_root / relative)) as stream:
                    rate = stream.samplerate
                    audio = stream.read(rate * 7, dtype="float32", always_2d=True).mean(axis=1)
                if not audio.size or not np.any(audio):
                    writer.writerow((index, relative, "abstained", "empty_or_silent"))
                    continue
                if rate != 16000:
                    factor = gcd(rate, 16000)
                    audio = resample_poly(audio, 16000 // factor, rate // factor)
                vector = verifier.embedding(audio)
            except (OSError, RuntimeError, ValueError) as error:
                writer.writerow((index, relative, "failed", str(error)))
                continue
            indices.append(index)
            vectors.append(vector)
            writer.writerow((index, relative, "scored", ""))
    temporary = args.output / "embeddings.part.npz"
    np.savez(temporary, indices=np.asarray(indices, dtype=np.int64), vectors=np.asarray(vectors))
    temporary.rename(args.output / "embeddings.npz")


if __name__ == "__main__":
    main()
