"""Opt-in ECAPA wiring smoke test against a local server with speaker assets.

Test tone is used as both probe and reference to check model loading only.
Does NOT measure genuine/impostor verification or session robustness.
"""
import io
import json
import sys

import httpx
import numpy as np
import soundfile as sf


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8767"
    rate = 16000
    samples = 0.08 * np.sin(
        2 * np.pi * 220 * np.arange(12 * rate, dtype=np.float32) / rate
    )
    data = io.BytesIO()
    sf.write(data, samples, rate, format="WAV", subtype="PCM_16")
    encoded = data.getvalue()
    with httpx.Client(base_url=base, timeout=240) as client:
        health = client.get("/health")
        health.raise_for_status()
        assert health.json()["speaker_verification"] == "ready"
        result = client.post("/analyze",
                             files={"file": ("probe.wav", encoded, "audio/wav"),
                                    "reference": ("enrollment.wav", encoded, "audio/wav")})
        result.raise_for_status()
        row = result.json()
    speaker = row["speaker_verification"]
    assert row["decision"] == "uncertain"
    assert row["prediction"]["label"] in ("Human", "AI-generated", "Unknown")
    assert speaker["score_type"] == "cosine_similarity"
    assert -1 <= speaker["similarity"] <= 1
    print(json.dumps({"status": "passed", "speaker_similarity": speaker["similarity"],
                      "matched_by_research_cutoff": speaker["matched"],
                      "label": row["prediction"]["label"],
                      "decision": row["decision"],
                      "warning": "Identical tone used for enrollment and probe; "
                                 "integration check only, not speaker validation."},
                     indent=2))


if __name__ == "__main__":
    main()
