"""Offline browser dashboard and upload-boundary regression tests."""
from io import BytesIO
from pathlib import Path

import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

from voicegaurd_runtime.api import create_app
from voicegaurd_runtime.inference import VoicegaurdInference
from voicegaurd_runtime.web_demo import verify_assets


class DummyEngine:
    def analyze(self, path):
        self.last_path = Path(path)
        assert path.is_file()
        assert path.read_bytes() == b"example"
        return {"evidence": {"synthetic": {"score": 0.2},
                             "replay": {"score": 0.8}},
                "speaker_verification": "unavailable"}


class FullWindowDetector:
    seconds = 4.0375

    def __init__(self, value):
        self.value = value

    def score(self, samples):
        # The real Detector accepts the full audio and crops internally.
        assert len(samples) >= 64600
        return {"score": self.value, "calibrated": False,
                "checkpoint": "test-only", "window_seconds": self.seconds}


def wav_bytes(seconds=9, rate=16000, amplitude=0.1):
    out = BytesIO()
    sf.write(out, np.full(int(seconds * rate), amplitude, np.float32),
             rate, format="WAV")
    return out.getvalue()


def test_dashboard_is_present_and_all_assets_are_local():
    client = TestClient(create_app())
    html = client.get("/")
    assert html.status_code == 200
    assert "Voicegaurd" in html.text
    assert "Uncertain" in html.text or "uncertain" in html.text
    assert "/static/app.js" in html.text
    assert html.headers["Cache-Control"] == "no-store"
    assert "frame-ancestors 'none'" in html.headers["Content-Security-Policy"]
    assert client.get("/static/styles.css").status_code == 200
    assert "getUserMedia" in client.get("/static/app.js").text
    assert client.get("/static/not-here.js").status_code == 404


def test_models_unavailable_does_not_accept_recordings():
    client = TestClient(create_app())
    assert client.get("/health").json() == {
        "status": "models_unavailable",
        "speaker_verification": "unavailable",
        "model_decision": "uncertain",
        "offline": True,
    }
    assert client.post("/analyze", files={"file": ("a.wav", b"data")}).status_code == 503


def test_upload_result_is_uncertain_and_temp_file_removed():
    engine = DummyEngine()
    client = TestClient(create_app(engine))
    response = client.post("/analyze",
                           files={"file": ("../../probe.wav", b"example")})
    assert response.status_code == 200
    assert response.json()["decision"] == "uncertain"
    assert response.json()["calibrated"] is False
    assert not engine.last_path.exists()


def test_origin_and_host_guards():
    client = TestClient(create_app(DummyEngine()))
    file = {"file": ("a.wav", b"example")}
    assert client.post("/analyze", files=file,
                       headers={"Origin": "https://malicious.example"}).status_code == 403
    assert client.post("/analyze", files=file,
                       headers={"Origin": "http://testserver"}).status_code == 200
    assert client.get("/health", headers={"Host": "external.example"}).status_code == 400


def test_scan_rejects_replay_only_without_scan():
    client = TestClient(create_app(DummyEngine()))
    response = client.post("/analyze?scan_replay=true",
                           files={"file": ("a.wav", b"example")})
    assert response.status_code == 422


def test_scans_full_windows_and_reports_short_audio_abstention():
    engine = VoicegaurdInference({
        "synthetic": FullWindowDetector(0.25),
        "replay": FullWindowDetector(0.70),
    })
    client = TestClient(create_app(engine))
    response = client.post(
        "/analyze?scan=true&scan_replay=true",
        files={"file": ("sample.wav", wav_bytes(9))}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["decision"] == "uncertain"
    assert body["evidence"]["synthetic"]["score"] == 0.25
    assert body["evidence"]["replay"]["score"] == 0.70
    assert len(body["synthetic_file_scan"]["windows"]) == 3
    assert len(body["replay_file_scan"]["windows"]) == 3
    assert body["replay_file_scan"]["windows"][-1]["end_seconds"] == 9.0

    short = client.post("/analyze?scan=true",
                        files={"file": ("short.wav", wav_bytes(1))})
    assert short.status_code == 200
    assert short.json()["decision"] == "uncertain"
    assert short.json()["evidence"]["synthetic"]["score"] is None
    assert short.json()["synthetic_file_scan"]["windows"] == []


def test_speaker_requires_model_and_uses_per_request_enrollment():
    engine = VoicegaurdInference({"synthetic": FullWindowDetector(0.1)})
    client = TestClient(create_app(engine))
    payload = {"file": ("probe.wav", wav_bytes()), "reference": ("ref.wav", wav_bytes())}
    assert client.post("/analyze", files=payload).status_code == 422

    class FakeSpeaker:
        def enroll(self, refs):
            assert len(refs) == 1 and refs[0].size == 16000 * 9
            return "enrolled"

        def verify(self, samples, template):
            assert template == "enrolled"
            return {"score_type": "cosine_similarity", "similarity": 0.77,
                    "matched": True, "threshold": 0.4}

    with_speaker = TestClient(create_app(engine, speaker_verifier=FakeSpeaker()))
    got = with_speaker.post("/analyze", files=payload)
    assert got.status_code == 200, got.text
    assert got.json()["speaker_verification"]["similarity"] == 0.77
    assert got.json()["decision"] == "uncertain"


def test_web_asset_verification_fails_closed(tmp_path):
    for relative in ("la/best.pt", "pa/best.pt",
                     "assets/wavlm-base-plus/config.json",
                     "assets/wavlm-base-plus/model.safetensors"):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("bad")
    import pytest
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        verify_assets(tmp_path)
