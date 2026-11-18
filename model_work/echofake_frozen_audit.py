"""Bounded, read-only EchoFake development audit of Voicegaurd's frozen LA/PA.

This is an exploratory *nonrandom block sample* of EchoFake dev metadata.
Do not reuse it to tune thresholds or assert independent/test performance.
It CANNOT establish speaker robustness or joint speaker-risk validation:
EchoFake lacks verified capture-session/enrollment claims on these rows.

Example from Voicegaurd repo (with its staged model environment):
 python model_work/echofake_frozen_audit.py --demo-root "..." --output "..."
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import random
from statistics import mean, median
from tempfile import TemporaryDirectory
from urllib.parse import quote, urlsplit

import httpx

REVISION = "4d8bd5f8458b55770d9cac6b944c7bd016168d3a"
DATASET = "EchoFake/EchoFake"
LA_CUTOFF = 0.0061066979542373995
PA_CUTOFF = 0.9364579916000366
CLASS_OFFSETS = {
    "bonafide": 0,
    "replay_bonafide": 1800,
    "fake": 2800,
    "replay_fake": 3500,
}
DATASET_API = "https://datasets-server.huggingface.co/rows"


def bounded_get(client, url, *, max_bytes):
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname != "datasets-server.huggingface.co":
        raise ValueError("Unexpected public dataset asset host")
    with client.stream("GET", url) as response:
        response.raise_for_status()
        contents = bytearray()
        for chunk in response.iter_bytes(chunk_size=65536):
            contents.extend(chunk)
            if len(contents) > max_bytes:
                raise ValueError("Audio exceeds download cap")
    return bytes(contents)


def audio_url(row):
    path = row.get("path")
    if isinstance(path, list) and path:
        path = path[0]
    return path.get("src") if isinstance(path, dict) else None


def cohort_rows(client, per_class, seed):
    if per_class < 1 or per_class > 80:
        raise ValueError("per_class must be between 1 and 80")
    rng = random.Random(seed)
    choices = []
    coverage = {}
    for label, offset in CLASS_OFFSETS.items():
        params = {"dataset": DATASET, "config": "default", "split": "dev",
                  "offset": offset, "length": 100}
        response = client.get(DATASET_API, params=params)
        response.raise_for_status()
        payload = response.json()
        rows = [item["row"] for item in payload["rows"]]
        candidates = [row for row in rows if row.get("label") == label
                      and audio_url(row)]
        coverage[label] = {"offset": offset, "block_rows": len(rows),
                           "eligible_in_block": len(candidates)}
        if len(candidates) < per_class:
            raise ValueError(f"Insufficient examples for {label} at offset {offset}")
        choices.extend(rng.sample(candidates, per_class))
    # Fix the first-listed audio revision and document this nonrandom cohort.
    return choices, coverage


def audit(args):
    from voicegaurd_runtime.audio import load_audio
    from voicegaurd_runtime.web_demo import verify_assets, build_engine
    from voicegaurd_runtime.labels import prediction_label

    root = verify_assets(args.demo_root)
    import os
    import sys
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    sys.path.insert(0, str(root / "assets"))

    with httpx.Client(timeout=25, follow_redirects=False,
                      headers={"User-Agent": "Voicegaurd-EchoFake-BoundedAudit/1.0"}) as client:
        rows, sampled_blocks = cohort_rows(client, args.per_class, args.seed)
        print(json.dumps({"stage": "manifest", "rows": len(rows),
                          "sampled_blocks": sampled_blocks}, indent=2), flush=True)
        if args.metadata_only:
            return {"sampled_blocks": sampled_blocks, "rows_selected": len(rows),
                    "note": "Audio was not downloaded"}
        engine = build_engine(root)
        result_rows = []
        with TemporaryDirectory(prefix="vg-echo-dev-") as scratch:
            scratch = Path(scratch)
            for count, row in enumerate(rows, 1):
                ground_truth = row["label"]
                key = row["utt_id"]
                audio = audio_url(row)
                record = {
                    "utterance_id": key,
                    "label_source": "EchoFake official dev metadata",
                    "ground_truth_class": ground_truth,
                    "true_synthetic": ground_truth in {"fake", "replay_fake"},
                    "true_replay": ground_truth in {"replay_bonafide", "replay_fake"},
                    "speaker_id_present": bool(row.get("source_speaker_id")),
                    "session_id_verified": False,
                    "enrollment_id_verified": False,
                    "audio_sha256": None,
                    "duration_seconds": None,
                    "la_raw": None, "pa_raw": None,
                    "predicted_label": "Unknown",
                    "la_hit": None, "pa_hit": None,
                    "status": "pending", "failure": None,
                }
                path = scratch / (key + ".mp3")
                try:
                    raw = bounded_get(client, audio, max_bytes=args.max_bytes)
                    record["audio_sha256"] = hashlib.sha256(raw).hexdigest()
                    path.write_bytes(raw)
                    samples, metadata = load_audio(path)
                    record["duration_seconds"] = metadata["duration"]
                    analysis = engine.analyze_samples(samples)
                    la = analysis["evidence"]["synthetic"]
                    pa = analysis["evidence"]["replay"]
                    record["la_raw"] = la.get("score")
                    record["pa_raw"] = pa.get("score")
                    record["predicted_label"] = prediction_label(analysis)["label"]
                    record["la_hit"] = (record["la_raw"] >= LA_CUTOFF
                                        if record["la_raw"] is not None else None)
                    record["pa_hit"] = (record["pa_raw"] >= PA_CUTOFF
                                        if record["pa_raw"] is not None else None)
                    record["status"] = (
                        "scored" if record["la_hit"] is not None
                        and record["pa_hit"] is not None else "abstained"
                    )
                except Exception as error:
                    record["status"] = "failed"
                    record["failure"] = f"{type(error).__name__}: {str(error)[:120]}"
                finally:
                    path.unlink(missing_ok=True)
                    result_rows.append(record)
                    print(f"{count}/{len(rows)} {ground_truth}: {record['status']}",
                          flush=True)
        output = args.output
        output.mkdir(parents=True, exist_ok=True)
        with (output / "rows.csv").open("w", encoding="utf-8", newline="") as sink:
            writer = csv.DictWriter(sink, fieldnames=result_rows[0].keys())
            writer.writeheader()
            writer.writerows(result_rows)
        class_results = {}
        for label in CLASS_OFFSETS:
            group = [r for r in result_rows if r["ground_truth_class"] == label]
            scored = [r for r in group if r["status"] == "scored"]
            class_results[label] = {
                "selected": len(group), "scored": len(scored),
                "abstained": sum(r["status"] == "abstained" for r in group),
                "failed": sum(r["status"] == "failed" for r in group),
                "LA_flagged": sum(r["la_hit"] is True for r in scored),
                "PA_flagged": sum(r["pa_hit"] is True for r in scored),
                "LA_median": median(r["la_raw"] for r in scored) if scored else None,
                "PA_median": median(r["pa_raw"] for r in scored) if scored else None,
            }
        scored = [r for r in result_rows if r["status"] == "scored"]
        result = {
            "dataset": DATASET, "revision": REVISION,
            "subset": "dev", "sampling": "Fixed-seed stratified draws from four "
                        "nonrandom contiguous 100-row blocks",
            "seed": args.seed, "per_class": args.per_class,
            "frozen_cutoffs": {"LA": LA_CUTOFF, "PA": PA_CUTOFF},
            "selected": len(rows), "scored": len(scored),
            "failed": len([r for r in result_rows if r["status"] == "failed"]),
            "abstained": len([r for r in result_rows if r["status"] == "abstained"]),
            "classes": class_results,
            "speaker_gate": "NOT_TESTABLE: source_speaker_id alone does not "
                            "prove session-disjoint enrollment/probes",
            "joint_gate": "NOT_TESTABLE: claimed/actual speaker and independent "
                          "enrollment labels unavailable on these audio trials",
            "independent_assessment": False,
            "qualification": "Development-only exploratory descriptive audit; "
                             "thresholds frozen; file source not representative "
                             "of live microphone input; results are not a deployment pass.",
        }
        (output / "summary.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(result, indent=2), flush=True)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--per-class", type=int, default=12)
    parser.add_argument("--seed", type=int, default=20261118)
    parser.add_argument("--max-bytes", type=int, default=4 * 1024 * 1024)
    parser.add_argument("--metadata-only", action="store_true")
    args = parser.parse_args()
    audit(args)


if __name__ == "__main__":
    main()
