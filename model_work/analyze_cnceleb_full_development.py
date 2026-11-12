"""Compare enrollment strategies using reconciled development embeddings."""
import csv
import json
from pathlib import Path
import sys

import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve

manifest, embeddings, output = map(Path, sys.argv[1:])
with manifest.open(newline="") as handle:
    rows = list(csv.DictReader(handle))
with np.load(embeddings, allow_pickle=False) as data:
    vectors = dict(zip(data["indices"].tolist(), data["vectors"]))
frozen = 0.4769288897514343


def trials(split, two_references):
    refs, probes = {}, []
    for index, row in enumerate(rows):
        if row["split"] != split:
            continue
        if row["role"] == "probe":
            probes.append((index, row["speaker"], row["genre"]))
        else:
            refs.setdefault(row["speaker"], {})[row["role"]] = vectors.get(index)
    names = sorted(refs)
    templates = {}
    for speaker, refs_for_speaker in refs.items():
        first = refs_for_speaker["reference_a"]
        second = refs_for_speaker["reference_b"]
        if first is None or (two_references and second is None):
            continue
        template = first + second if two_references else first
        norm = np.linalg.norm(template)
        if norm > 0:
            templates[speaker] = template / norm
    scored = [(vectors[i], speaker, genre) for i, speaker, genre in probes if i in vectors]
    valid_names = sorted(templates)
    scores = np.clip(np.stack([x[0] for x in scored]) @ np.stack([templates[s] for s in valid_names]).T, -1, 1)
    targets = np.asarray([x[1] for x in scored])[:, None] == np.asarray(valid_names)[None, :]
    genres = np.asarray([x[2] for x in scored])
    planned = {g: sum(row[2] == g for row in probes) * len(names) for g in {row[2] for row in probes}}
    return scores, targets, genres, planned


def metrics(scores, targets, cutoff, planned):
    positives, negatives = scores[targets], scores[~targets]
    result = dict(planned=planned, scored=scores.size, abstained=planned - scores.size,
                  targets=positives.size, impostors=negatives.size,
                  false_rejects=int((positives <= cutoff).sum()),
                  false_accepts=int((negatives > cutoff).sum()))
    result["frr"] = result["false_rejects"] / positives.size if positives.size else None
    result["far"] = result["false_accepts"] / negatives.size if negatives.size else None
    return result


summary = {"scope": "CN-Celeb1 development only; pair-weighted metrics",
           "frozen_cutoff": frozen, "nominal_calibration_far": 0.01, "methods": {}}
for method in ("single", "two"):
    cal, cal_target, _, cal_plan = trials("calibration", method == "two")
    impostors = cal[~cal_target]
    rank = impostors.size - 1 - int(0.01 * impostors.size)
    cutoff = float(np.partition(impostors, rank)[rank])
    scores, targets, genres, planned = trials("validation", method == "two")
    fpr, tpr, _ = roc_curve(targets.ravel(), scores.ravel())
    fnr = 1 - tpr
    crossing = np.argmin(np.abs(fpr - fnr))
    summary["methods"][method] = {
        "candidate_cutoff": cutoff,
        "candidate_calibration": metrics(cal, cal_target, cutoff, sum(cal_plan.values())),
        "frozen_validation": metrics(scores, targets, frozen, sum(planned.values())),
        "candidate_validation": metrics(scores, targets, cutoff, sum(planned.values())),
        "validation_auc": float(roc_auc_score(targets.ravel(), scores.ravel())),
        "validation_eer_percent": float(50 * (fpr[crossing] + fnr[crossing])),
        "by_genre": {genre: {"frozen": metrics(scores[genres == genre], targets[genres == genre], frozen, count),
                              "candidate": metrics(scores[genres == genre], targets[genres == genre], cutoff, count)}
                     for genre, count in sorted(planned.items())},
    }
with output.open("x", encoding="utf-8") as handle:
    json.dump(summary, handle, indent=2)
