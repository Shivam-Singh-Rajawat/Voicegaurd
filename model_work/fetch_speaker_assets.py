"""Fetch a pinned official SpeechBrain model for offline HPC use."""
import hashlib
import json
import urllib.request
from pathlib import Path

REVISION = "0f99f2d0ebe89ac095bcc5903c4dd8f72b367286"
FILES = ["README.md", "hyperparams.yaml", "embedding_model.ckpt",
         "mean_var_norm_emb.ckpt", "classifier.ckpt", "label_encoder.txt",
         "config.json"]
out = Path(__file__).parent / "speaker_assets"
out.mkdir(exist_ok=True)
records = []
for name in FILES:
    path = out / name
    url = f"https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb/resolve/{REVISION}/{name}"
    if not path.exists():
        temporary = path.with_suffix(path.suffix + ".partial")
        with urllib.request.urlopen(url, timeout=60) as response, temporary.open("wb") as target:
            while chunk := response.read(1024 * 1024):
                target.write(chunk)
        temporary.replace(path)
    records.append(dict(file=name, bytes=path.stat().st_size,
                        sha256=hashlib.sha256(path.read_bytes()).hexdigest(), source=url))
    print(name, path.stat().st_size, flush=True)
(out / "PROVENANCE.json").write_text(json.dumps(dict(
    repository="speechbrain/spkrec-ecapa-voxceleb", revision=REVISION,
    license="Apache-2.0 according to official model card",
    status="downloaded; inference and local evaluation not yet verified", files=records), indent=2))
