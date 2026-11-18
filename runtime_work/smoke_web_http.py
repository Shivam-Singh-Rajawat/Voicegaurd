"""Run an opt-in live HTTP smoke test against the local Voicegaurd V1 server.

Requires the server already running on localhost with the real checkpoints.
Uses only generated tone audio, not any personal recording or test dataset.
"""
import io
import json
import sys

import httpx
import numpy as np
import soundfile as sf


def main():
    base = "http://127.0.0.1:8765"
    if len(sys.argv) > 1:
        base = sys.argv[1].rstrip("/")
    with httpx.Client(base_url=base, timeout=240) as client:
        health = client.get("/health")
        health.raise_for_status()
        assert health.json()["status"] == "ready", health.text
        assert client.get("/").status_code == 200
        assert client.get("/static/app.js").status_code == 200
        assert client.get("/static/styles.css").status_code == 200
        rate = 16000
        seconds = 12
        samples = 0.08 * np.sin(
            2 * np.pi * 220 * np.arange(seconds * rate, dtype=np.float32) / rate
        )
        memory = io.BytesIO()
        sf.write(memory, samples, rate, format="WAV", subtype="PCM_16")
        response = client.post(
            "/analyze?scan=true&scan_replay=true",
            files={"file": ("synthetic-tone-test.wav", memory.getvalue(), "audio/wav")},
        )
        response.raise_for_status()
        report = response.json()
        assert report["decision"] == "uncertain"
        assert report["prediction"]["label"] in ("Human", "AI-generated", "Unknown")
        assert report["prediction"]["security_decision"] == "uncertain"
        assert report["prediction"]["label_validation"] == "not_validated_for_this_input"
        assert report["calibrated"] is False
        assert report["input_source"] == "uploaded_audio"
        assert report["audio"]["duration"] == seconds
        assert report["speaker_verification"] == "unavailable"
        for detector in ("synthetic", "replay"):
            score = report["evidence"][detector]["score"]
            assert isinstance(score, float) and 0 <= score <= 1
            assert report["evidence"][detector]["calibrated"] is False
            assert len(report[f"{detector}_file_scan"]["windows"]) == 3
        print(json.dumps({
            "status": "passed",
            "fixture": "12-second generated sine tone",
            "decision": report["decision"],
            "synthetic_score": report["evidence"]["synthetic"]["score"],
            "replay_score": report["evidence"]["replay"]["score"],
            "synthetic_windows": len(report["synthetic_file_scan"]["windows"]),
            "replay_windows": len(report["replay_file_scan"]["windows"]),
            "note": "Integration only; no accuracy inference from a tone",
        }, indent=2))


if __name__ == "__main__":
    main()
