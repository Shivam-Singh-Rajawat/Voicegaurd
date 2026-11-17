import numpy as np
import pytest
from voicegaurd_runtime.inference import fixed_window, VoicegaurdInference
from voicegaurd_runtime.microphone_demo import scan_synthetic_windows
from voicegaurd_runtime import microphone_demo


def test_window_matches_existing_center_crop():
    assert fixed_window(np.arange(8), 4).tolist() == [2, 3, 4, 5]
    with pytest.raises(ValueError, match="complete model window"):
        fixed_window([1, 2], 5)


@pytest.mark.parametrize("samples", [[], [float("nan")], [[1, 2]]])
def test_bad_samples_rejected(samples):
    with pytest.raises(ValueError):
        fixed_window(samples, 4)


def test_unknown_detector_rejected():
    with pytest.raises(ValueError):
        VoicegaurdInference({"invented": object()})


class FullWindowDetector:
    seconds = 4.0375

    def score(self, samples):
        assert len(samples) == 64600
        return {"score": 0.25, "calibrated": False}


def test_file_scan_only_scores_full_windows_and_covers_tail():
    detector = FullWindowDetector()
    width = 64600
    assert scan_synthetic_windows(np.ones(width - 1), 16000, detector) == []
    samples = np.concatenate([np.zeros(width), np.ones(width + 8000)])
    windows = scan_synthetic_windows(samples, 16000, detector)
    assert [window["score"] for window in windows] == [None, 0.25, 0.25]
    assert [window["start_seconds"] for window in windows] == [0, 4.0375, 4.5375]
    assert windows[-1]["end_seconds"] == len(samples) / 16000


def test_microphone_demo_captures_twelve_seconds_without_padding(monkeypatch, tmp_path, capsys):
    import json
    import sys
    from types import SimpleNamespace

    import soundfile

    rate = 44100
    saved = tmp_path / "capture.wav"
    report_path = tmp_path / "evidence.json"
    monkeypatch.setattr(sys, "argv", [
        "microphone_demo", "--synthetic", "la.pt", "--replay", "pa.pt",
        "--save-recording", str(saved), "--scan-recording",
        "--scan-replay", "--output-json", str(report_path),
    ])
    monkeypatch.setattr("builtins.input", lambda prompt: None)
    torch = pytest.importorskip("torch")
    monkeypatch.setattr(torch, "set_num_threads", lambda _: None)

    def record(frames, *, samplerate, channels, dtype):
        assert (frames, samplerate, channels, dtype) == (rate * 12, rate, 1, "float32")
        return np.full((frames, channels), 0.1, dtype=dtype)

    class StubDetector:
        seconds = 4.0375

        def __init__(self, checkpoint):
            pass

        def score(self, samples):
            assert len(samples) in (16000 * 12, 64600)
            return {"score": 0.25, "calibrated": False}

    monkeypatch.setitem(sys.modules, "sounddevice", SimpleNamespace(
        query_devices=lambda **_: {"default_samplerate": rate},
        rec=record, wait=lambda: None,
    ))
    monkeypatch.setattr(microphone_demo, "Detector", StubDetector)
    microphone_demo.main()

    result = json.loads(capsys.readouterr().out.split("Recording…\n", 1)[1])
    assert result["input_source"] == "microphone"
    assert result["audio"]["duration"] == 12
    assert result["voice_origin"]["verdict"] == "uncertain"
    windows = result["synthetic_microphone_scan"]["windows"]
    assert len(windows) == 3
    assert windows[-1]["end_seconds"] == 12
    replay = result["replay_microphone_scan"]
    assert replay["calibrated"] is False
    assert len(replay["windows"]) == 3
    assert replay["windows"][-1]["end_seconds"] == 12
    assert json.loads(report_path.read_text(encoding="utf-8")) == result
    assert soundfile.info(saved).frames == rate * 12


def test_short_audio_abstains_at_inference_entry_point():
    inference = VoicegaurdInference({"synthetic": FullWindowDetector()})
    evidence = inference.analyze_samples(np.ones(32000))["evidence"]["synthetic"]
    assert evidence["status"] == "insufficient_audio"
    assert evidence["score"] is None
    assert inference.analyze_samples(np.ones(64600))["evidence"]["synthetic"]["score"] == 0.25


def test_stream_matches_full_window_and_does_not_share_audio():
    inference = VoicegaurdInference({"synthetic": FullWindowDetector()})
    audio = np.ones(64600)
    first = inference.open_stream()
    second = inference.open_stream()
    assert first.push(audio[:32000]) == []
    assert second.push(audio[32000:]) == []
    assert first.push(audio[32000:]) == [dict(start_seconds=0.0, **inference.analyze_samples(audio))]
    first.reset()
    assert first.push(audio[:32000]) == []


def test_stream_reports_speaker_evidence_and_abstains_on_no_signal():
    class Verifier:
        def verify(self, samples, template):
            assert len(samples) == 64600 and template == "enrolled"
            return {"similarity": 0.8, "matched": True}

    inference = VoicegaurdInference({"synthetic": FullWindowDetector()},
                                    speaker_verifier=Verifier(), speaker_template="enrolled")
    short = inference.analyze_samples(np.ones(32000))
    assert short["speaker_verification"]["status"] == "insufficient_audio"
    silent = inference.analyze_samples(np.zeros(64600))
    assert silent["speaker_verification"]["matched"] is None
    assert silent["evidence"]["synthetic"]["status"] == "no_signal"
    stream = inference.open_stream()
    assert stream.push(np.ones(32000)) == []
    result = stream.push(np.ones(32600))[0]
    assert result["speaker_verification"] == {"similarity": 0.8, "matched": True}


@pytest.mark.parametrize("extra,expected", [
    (["--scan-replay"], "requires --scan-file or --scan-recording"),
    (["--output-json", "existing.json"], "Choose a NEW JSON path"),
    (["--output-json", "wrong.txt"], "needs a .json destination"),
])
def test_report_and_replay_flags_validate_before_model_loading(
    monkeypatch, tmp_path, capsys, extra, expected
):
    import sys
    monkeypatch.chdir(tmp_path)
    (tmp_path / "existing.json").write_text("original", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        "microphone_demo", "--synthetic", "la.pt", "--replay", "pa.pt",
        "--smoke-test", *extra,
    ])
    with pytest.raises(SystemExit) as error:
        microphone_demo.main()
    assert error.value.code == 2
    assert expected in capsys.readouterr().err
    assert (tmp_path / "existing.json").read_text(encoding="utf-8") == "original"
