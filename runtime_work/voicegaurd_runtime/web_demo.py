"""Offline Windows browser demo backed by pinned Voicegaurd research checkpoints.

Run from the repo's runtime_work on PYTHONPATH using Start-WebDemo.ps1.
Only serves 127.0.0.1; not a remote or public-facing service.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

_HASHES = {
    "la/best.pt": "5600846905b143a476ec83cd805b44536fae166102fe015ea3ed2b84e026a57b",
    "pa/best.pt": "21c4f85791204ff215dc88a3944bb53e056c614bb3f675994f33397268ba7b09",
    "assets/wavlm-base-plus/config.json": "fea6df1c2700a3954fc07e70588aecc9055eeb28db2ff57151a2db0d19180ed4",
    "assets/wavlm-base-plus/model.safetensors": "1a252e49ddf1897f1f07f0d73c2a7cca86a05b0ad8d0189a6edc0ad3e55f1ae6",
}


def verify_assets(root):
    """Refuse mismatched or incomplete model assets, never redownload."""
    root = Path(root).resolve()
    for relative, expected in _HASHES.items():
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(f"Required Voicegaurd model asset missing: {path}")
        with path.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        if digest.lower() != expected:
            raise ValueError(f"Model asset SHA-256 mismatch: {path}")
    if not (root / "assets" / "voicegaurd_v3").is_dir():
        raise FileNotFoundError("Local voicegaurd_v3 model loader missing")
    return root


def build_engine(root):
    import torch
    from .inference import Detector, VoicegaurdInference
    torch.set_num_threads(min(4, torch.get_num_threads()))
    return VoicegaurdInference({
        "synthetic": Detector(root / "la" / "best.pt"),
        "replay": Detector(root / "pa" / "best.pt"),
    })


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo-root", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--speaker-assets", type=Path)
    parser.add_argument("--smoke-test", action="store_true",
                        help="Verify pinned models on a test tone without starting HTTP")
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a port from 1024 to 65535")
    root = verify_assets(args.demo_root)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    sys.path.insert(0, str(root / "assets"))

    engine = build_engine(root)
    if args.smoke_test:
        import numpy as np
        length = round(engine.window_seconds * 16000) + 16000
        samples = 0.1 * np.sin(
            2 * np.pi * 220 * np.arange(length, dtype=np.float32) / 16000
        )
        result = engine.analyze_samples(samples)
        print(json.dumps({"test_input": "sine_tone", "decision": "uncertain",
                          **result}, indent=2))
        return 0

    from .api import create_app
    import uvicorn
    with TemporaryDirectory(prefix="voicegaurd-web-session-") as directory:
        verifier = None
        if args.speaker_assets:
            from .speaker import SpeakerVerifier
            verifier = SpeakerVerifier.from_pretrained(
                args.speaker_assets, Path(directory) / "speaker", 0.4769288897514343)
        app = create_app(engine, speaker_verifier=verifier)
        print(f"Voicegaurd V1 ready at http://127.0.0.1:{args.port}", flush=True)
        print("Offline inference only. Press Ctrl+C to stop.", flush=True)
        uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning",
                    access_log=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
