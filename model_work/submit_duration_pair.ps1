$job = @'
#!/bin/bash
#PBS -N vg_durpair
#PBS -q workq
#PBS -l select=1:ncpus=4:mem=12gb
#PBS -l walltime=00:20:00
#PBS -j oe
set -euo pipefail
cd "$HOME/voicegaurd"
export PYTHONPATH="$PWD" CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
exec > "logs/duration_pair_${PBS_JOBID}.log" 2>&1
.venv/bin/python - <<'PY'
import json
import os
from pathlib import Path

import pandas as pd
from voicegaurd_runtime.audio import load_audio
from voicegaurd_runtime.inference import Detector, fixed_window

root = Path.cwd()
out = root / "reports" / ("duration_pair_" + os.environ["PBS_JOBID"])
out.mkdir()
source = pd.read_csv(root / "manifests/v3/la_select.csv")
candidates = source[source.label == 0].sample(frac=1, random_state=20261109)
calibration = pd.read_csv(root / "reports/temperature_calibration_46013.mgmt01/development_comparison.csv")
threshold = float(calibration.loc[(calibration.domain == "la") & (calibration.method == "raw"), "calibration_threshold"].item())
model = Detector(root / "checkpoints/v3_wavlm_attn_20_fixed/best.pt")
window_samples = round(model.seconds * 16000)
rows = []
selected = 0
for record in candidates.itertuples():
    audio, metadata = load_audio(record.path)
    if audio.size < window_samples:
        continue
    full = fixed_window(audio, window_samples)
    baseline = model.score(full)["score"]
    for seconds in (0.5, 1.0, 2.0, 3.0):
        crop = fixed_window(full, round(seconds * 16000))
        score = model.score(crop)["score"]
        rows.append({"uid": record.uid, "speaker": record.speaker_id, "seconds": seconds, "baseline": baseline, "score": score})
    selected += 1
    if selected % 20 == 0:
        print("Processed", selected, flush=True)
    if selected == 120:
        break
assert selected == 120
scores = pd.DataFrame(rows)
scores.to_csv(out / "paired_scores.csv", index=False)
summary = []
for seconds, frame in scores.groupby("seconds"):
    before = frame.baseline > threshold
    after = frame.score > threshold
    summary.append({"seconds": seconds, "baseline_flags": int(before.sum()), "crop_flags": int(after.sum()), "new_flags": int((~before & after).sum()), "removed_flags": int((before & ~after).sum())})
result = {"files": selected, "threshold": threshold, "full_window_seconds": model.seconds, "scope": "Paired LA development bona fide clips. Center truncation and the existing repeat-to-window preprocessing act together. No threshold refit.", "results": summary}
(out / "summary.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
PY

'@
$job | ssh -i "$env:USERPROFILE\.ssh\voicegaurd_codex" -o BatchMode=yes -o ConnectTimeout=7 -o ServerAliveInterval=5 -o ServerAliveCountMax=2 shivam.15279@10.16.1.50 'tr -d ''\015'' | /opt/pbs/bin/qsub'
exit $LASTEXITCODE
