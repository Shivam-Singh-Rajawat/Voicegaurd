"""Collect research evidence without loading models or changing checkpoints."""
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone


def audit(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    result = {"generated_utc": datetime.now(timezone.utc).isoformat(),
              "root": str(root), "records": [], "warnings": [],
              "interpretation": "Learning curves alone cannot establish absence of overfit or underfit. Compare fixed train/dev metrics, split integrity, checkpoint selection and untouched evaluation."}
    candidates = set()
    for base in (root / "checkpoints", root / "logs", root / "reports"):
        if not base.exists():
            continue
        for pattern in ("*history*.jsonl", "*history*.json", "training_summary.json"):
            candidates.update(base.rglob(pattern))
    for path in sorted(candidates):
        raw = path.read_bytes()
        entry = {"path": str(path.relative_to(root)),
                 "sha256": hashlib.sha256(raw).hexdigest()}
        try:
            text = raw.decode("utf-8")
            if path.suffix == ".jsonl":
                records = [json.loads(line) for line in text.splitlines() if line.strip()]
            else:
                records = json.loads(text)
            entry["content"] = records
            if isinstance(records, list):
                entry["record_count"] = len(records)
                entry["available_fields"] = sorted({key for row in records
                                                     if isinstance(row, dict) for key in row})
        except (ValueError, UnicodeError) as error:
            entry["error"] = str(error)
        result["records"].append(entry)
    if not candidates:
        result["warnings"].append("No matching training records found; training behavior unverified")
    (output / "training_evidence.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (output / "REVIEW_CHECKLIST.md").write_text(
        "# Model acceptance evidence\n\n"
        "- Verify official data splits, labels, speaker overlap and duplicates.\n"
        "- Compare fixed train/dev loss and discrimination metrics by epoch.\n"
        "- Check validation deterioration, checkpoint selection and early stopping.\n"
        "- Investigate weak training and validation scores before adding capacity.\n"
        "- Distinguish sampled training metrics from full development metrics.\n"
        "- Fit calibration only on its designated development subset.\n"
        "- Preserve independent test history; do not use it for hyperparameter tuning.\n"
        "- Report attack/speaker/domain performance and uncertainty.\n"
        "- Verify full-audio decoding and matched preprocessing.\n"
        "- Document unavailable data, language labels and licensing.\n"
        "- Record configuration, seeds, provenance and reproducible commands.\n",
        encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = audit(args.root, args.out)
    print(f"Collected {len(result['records'])} training records")
