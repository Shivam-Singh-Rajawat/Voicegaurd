"""Voicegaurd V1 microphone and local audio file demo."""
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from .inference import Detector, VoicegaurdInference


def scan_synthetic_windows(samples, sample_rate, detector):
    """Score only complete windows, including one ending at the file boundary."""
    import numpy as np

    width = round(detector.seconds * sample_rate)
    starts = list(range(0, len(samples) - width + 1, width))
    if starts and starts[-1] + width < len(samples):
        starts.append(len(samples) - width)
    windows = []
    for start in starts:
        window = samples[start:start + width]
        windows.append({
            "start_seconds": start / sample_rate,
            "end_seconds": (start + width) / sample_rate,
            "score": detector.score(window)["score"] if np.any(window) else None,
        })
    return windows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", required=True, type=Path)
    parser.add_argument("--replay", required=True, type=Path)
    parser.add_argument("--synthetic-research-cutoff", type=float,
                        help="Show a diagnostic comparison for the pinned LA checkpoint")
    parser.add_argument("--scan-file", action="store_true",
                        help="Report synthetic-voice scores across a supplied recording")
    parser.add_argument("--scan-recording", action="store_true",
                        help="Report synthetic-voice scores across the microphone capture")
    parser.add_argument("--speaker-assets", type=Path)
    parser.add_argument("--reference", type=Path, action="append", default=[])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--smoke-test", action="store_true", help="Score a test tone without recording")
    mode.add_argument("--audio", type=Path,
                      help="Analyze a file with at least 4.0375 seconds of audio. Use 8+ seconds of clear speech.")
    parser.add_argument("--save-recording", type=Path, help="Save microphone capture as a new WAV file")
    args = parser.parse_args()
    if args.scan_file and args.audio is None:
        parser.error("--scan-file requires --audio")
    if args.scan_recording and (args.audio is not None or args.smoke_test):
        parser.error("--scan-recording requires microphone mode")
    cutoff = args.synthetic_research_cutoff
    if cutoff is not None and not 0 <= cutoff <= 1:
        parser.error("Synthetic research cutoff must be between 0 and 1")
    if args.save_recording is not None:
        if args.audio is not None or args.smoke_test:
            parser.error("--save-recording requires microphone mode")
        if args.save_recording.suffix.lower() != ".wav":
            parser.error("--save-recording needs a .wav destination")
        if not args.save_recording.parent.is_dir() or args.save_recording.exists():
            parser.error("Choose a new WAV path in an existing folder")
    if bool(args.speaker_assets) != bool(args.reference):
        parser.error("Provide speaker assets and authorized reference audio together")

    import numpy as np
    import soundfile as sf
    import torch

    torch.set_num_threads(min(torch.get_num_threads(), 4))

    with TemporaryDirectory(prefix="voicegaurd-mic-") as directory:
        work = Path(directory)
        verifier = template = None
        if args.speaker_assets:
            from .audio import load_audio
            from .speaker import SpeakerVerifier
            verifier = SpeakerVerifier.from_pretrained(
                args.speaker_assets, work / "speaker", 0.4769288897514343
            )
            template = verifier.enroll([load_audio(path)[0] for path in args.reference])
        load_start = perf_counter()
        engine = VoicegaurdInference(
            {"synthetic": Detector(args.synthetic), "replay": Detector(args.replay)},
            speaker_verifier=verifier, speaker_template=template,
        )
        load_seconds = perf_counter() - load_start
        seconds = max(12, engine.window_seconds + 4)
        if args.audio is not None:
            path = args.audio
            source = "file"
        elif args.smoke_test:
            rate = 16000
            audio = 0.1 * np.sin(2 * np.pi * 220 * np.arange(round(rate * seconds)) / rate)
            source = "test_tone"
        else:
            import sounddevice as sd
            rate = round(sd.query_devices(kind="input")["default_samplerate"])
            input(f"Press Enter to record {seconds:g} seconds. Speak continuously "
                  "from the recording prompt for at least 8 seconds. ")
            print("Recording…", flush=True)
            audio = sd.rec(round(rate * seconds), samplerate=rate, channels=1, dtype="float32")
            sd.wait()
            source = "microphone"
        if args.audio is None:
            path = work / "capture.wav"
            sf.write(path, audio, rate, subtype="FLOAT")
        if args.save_recording is not None:
            with args.save_recording.open("xb") as destination:
                sf.write(destination, audio, rate, format="WAV", subtype="FLOAT")
        analyze_start = perf_counter()
        if args.scan_file or args.scan_recording:
            from .audio import load_audio

            samples, metadata = load_audio(path)
            result = dict(audio=metadata, **engine.analyze_samples(samples))
            detector = engine.detectors["synthetic"]
            scan_key = "synthetic_file_scan" if args.scan_file else "synthetic_microphone_scan"
            result[scan_key] = {
                "windows": scan_synthetic_windows(samples, metadata["sample_rate"], detector),
                "calibrated": False,
            }
        else:
            result = engine.analyze(path)
        analyze_seconds = perf_counter() - analyze_start
        synthetic = result["evidence"]["synthetic"]
        score = synthetic["score"]
        status = synthetic.get("status")
        if status == "insufficient_audio":
            reason = (f"Need at least {synthetic['window_seconds']:g} seconds of audio. "
                      "Use 8 or more seconds of clear speech.")
        elif status == "no_signal":
            reason = "The recording contains no audio signal."
        else:
            reason = "The LA cutoff has not been validated for this input."
        if score is None or cutoff is None:
            indication = "uncertain"
        elif score >= cutoff:
            indication = "synthetic_signal_detected"
        else:
            indication = "no_synthetic_signal_detected"
        print(json.dumps({
            "decision": "uncertain",
            "reason": "No validated joint decision policy for this acquisition.",
            "detector_load_seconds": round(load_seconds, 3),
            "analysis_seconds": round(analyze_seconds, 3),
            "input_source": source,
            "voice_origin": {
                "verdict": "uncertain",
                "reason": reason,
                "model_indication": indication,
                "research_cutoff": cutoff,
                "scope": "single centered window; cutoff unvalidated for this input",
            },
            **result,
        }, indent=2))


if __name__ == "__main__":
    main()
