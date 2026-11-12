$job = @'
#!/bin/bash
#PBS -N vg_corpcmp
#PBS -q workq
#PBS -l select=1:ncpus=1:mem=2gb
#PBS -l walltime=00:05:00
#PBS -j oe
set -euo pipefail
cd "$HOME/voicegaurd"
exec > "logs/corpus_comparison_${PBS_JOBID}.log" 2>&1
.venv/bin/python - <<'PY'
from pathlib import Path
import json
import os
import pandas as pd

reports = Path("reports")
pa = json.loads((reports / "v3_pa_auto/selected_model.json").read_text())
calibration = pd.read_csv(reports / "temperature_calibration_46013.mgmt01/development_comparison.csv")
thresholds = {
    "replay": float(pa["frozen_threshold"]),
    "synthetic": float(calibration.loc[(calibration.domain == "la") & (calibration.method == "raw"), "calibration_threshold"].item()),
}
results = {"thresholds": thresholds, "corpora": {}, "scope": "Unlabeled recording-source comparison. Threshold exceedance is descriptive and cannot estimate a false-positive rate. Identical sampled offsets within a file are counted once."}
for name, job in [("MUCS Hindi-English", "46024"), ("IndicVoices", "46048")]:
    scores = pd.read_csv(reports / f"hinglish_response_{job}.mgmt01/window_scores.csv")
    assert len(scores) == 300 and scores.path.nunique() == 100
    scores = scores.drop_duplicates(["path", "offset_seconds"])
    corpus = {"sampled_windows": 300, "distinct_offsets": len(scores), "files": int(scores.path.nunique()), "strata": {}}
    for label, subset in [("all", scores), ("rms_at_least_0_01", scores[scores.rms >= 0.01])]:
        result = {"windows": len(subset), "files": int(subset.path.nunique())}
        for model, threshold in thresholds.items():
            score = subset[model + "_score"]
            assert score.between(0, 1).all()
            flags = (score > threshold).groupby(subset.path).mean()
            result[model] = {"median": float(score.median()), "file_weighted_exceedance": float(flags.mean())} if len(score) else None
        corpus["strata"][label] = result
    results["corpora"][name] = corpus

out = reports / ("corpus_comparison_" + os.environ["PBS_JOBID"])
out.mkdir()
(out / "summary.json").write_text(json.dumps(results, indent=2, allow_nan=False))
print(json.dumps(results, indent=2, allow_nan=False))
PY

'@
$job | ssh -i "$env:USERPROFILE\.ssh\voicegaurd_codex" -o BatchMode=yes -o ConnectTimeout=8 -o ServerAliveInterval=5 -o ServerAliveCountMax=2 shivam.15279@10.16.1.50 'tr -d ''\015'' | /opt/pbs/bin/qsub -W depend=afterok:46048.mgmt01'
exit $LASTEXITCODE
