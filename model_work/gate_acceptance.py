"""Strict joint-audio validation gate checker.

This tool will NOT infer missing labels or cross-session provenance.
It calibrates an interpretable 3-threshold policy *only* on calibration
identities/sources and evaluates it once on strictly disjoint assessment.
A pass requires the approved limits with conservative confidence intervals.
No gate is passed without real trials and full scope-specific coverage.

Manifest columns are listed in RECORDED_AUDIO_JOINT_PROTOCOL.md plus
synthetic_score,replay_score,speaker_similarity.
"""
import argparse
from collections import defaultdict
import csv
import json
import math
from pathlib import Path

LA_BASELINE = 0.0061066979542373995
PA_BASELINE = 0.9364579916000366
SPEAKER_BASELINE = 0.4769288897514343

# Upper bounds for each acquisition scope, as previously approved.
LIMITS = {"target_reject": .10, "impostor_accept": .01,
          "synthetic_accept": .05, "replay_accept": .05,
          "abstention": .10}
REQUIRED = {
    "trial_id", "scope", "partition", "probe_sha256", "probe_session",
    "source_lineage", "actual_speaker", "claimed_speaker",
    "enrollment_sessions", "enrollment_sha256s", "relationship", "origin",
    "presentation", "label_provenance", "authorization_id", "synthetic_score",
    "replay_score", "speaker_similarity",
}
MISSING = {"", "unknown", "na", "none", "null", "missing", "?"}


def present(value):
    return str(value or "").strip().lower() not in MISSING


def verify_manifest(rows):
    if not rows:
        raise ValueError("No labeled trials supplied")
    missing = REQUIRED - set(rows[0])
    if missing:
        raise ValueError("Missing verified columns: " + ", ".join(sorted(missing)))
    ids = set()
    partition_people = defaultdict(set)
    partition_sources = defaultdict(set)
    partition_hashes = defaultdict(set)
    part_scopes = defaultdict(set)
    for row in rows:
        trial_id = row["trial_id"]
        if not present(trial_id) or trial_id in ids:
            raise ValueError("Duplicate or empty trial_id")
        ids.add(trial_id)
        if row["scope"] not in ("microphone", "file"):
            raise ValueError("Unknown acquisition scope: " + trial_id)
        if row["partition"] not in ("calibration", "assessment"):
            raise ValueError("Unknown partition: " + trial_id)
        if row["relationship"] not in ("target", "impostor"):
            raise ValueError("Unverified claimed-speaker relationship: " + trial_id)
        if row["origin"] not in ("human", "synthetic"):
            raise ValueError("Unknown human/synthetic label: " + trial_id)
        if row["presentation"] not in ("direct", "replay"):
            raise ValueError("Unknown direct/replay label: " + trial_id)
        required_meta = (
            "probe_sha256", "probe_session", "source_lineage",
            "actual_speaker", "claimed_speaker", "enrollment_sessions",
            "enrollment_sha256s", "label_provenance", "authorization_id"
        )
        if any(not present(row[k]) for k in required_meta):
            raise ValueError("Missing source/speaker/session/authorization provenance: " + trial_id)
        if any(not present(v) for v in row["enrollment_sessions"].split("|")):
            raise ValueError("Invalid enrollment session list: " + trial_id)
        if row["probe_session"] in row["enrollment_sessions"].split("|"):
            raise ValueError("Enrollment/probe session overlap: " + trial_id)
        if row["probe_sha256"] in row["enrollment_sha256s"].split("|"):
            raise ValueError("The probe is its own enrollment: " + trial_id)
        same_person = row["actual_speaker"] == row["claimed_speaker"]
        if same_person != (row["relationship"] == "target"):
            raise ValueError("Claimed vs actual identity contradicts label: " + trial_id)
        key = row["partition"]
        partition_people[key].update((row["actual_speaker"], row["claimed_speaker"]))
        partition_sources[key].add(row["source_lineage"])
        partition_hashes[key].add(row["probe_sha256"])
        part_scopes[key].add(row["scope"])
    for category, groups in (("speaker", partition_people),
                             ("source lineage", partition_sources),
                             ("audio bytes", partition_hashes)):
        intersection = groups["calibration"] & groups["assessment"]
        if intersection:
            raise ValueError(f"Calibration/assessment {category} overlap: "
                             f"{len(intersection)} groups")
    if not all(partition_people.get(p) for p in ("calibration", "assessment")):
        raise ValueError("Both calibration and held-out assessment are mandatory")
    return {"trials": len(rows),
            "calibration_speakers": len(partition_people["calibration"]),
            "assessment_speakers": len(partition_people["assessment"]),
            "scopes": sorted(part_scopes["assessment"])}


def score_value(row, name):
    value = str(row.get(name, "")).strip().lower()
    if value in MISSING:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Malformed {name}: {row.get('trial_id')}")
    low = -1 if name == "speaker_similarity" else 0
    if not math.isfinite(number) or not low <= number <= 1:
        raise ValueError(f"Out-of-range {name}: {row.get('trial_id')}")
    return number


def decision(row, thresholds, *, speaker_only=False):
    speaker = score_value(row, "speaker_similarity")
    if speaker is None:
        return "abstain"
    match = speaker > thresholds["speaker"]
    if speaker_only:
        return "accept" if match else "reject"
    la = score_value(row, "synthetic_score")
    pa = score_value(row, "replay_score")
    if la is None or pa is None:
        return "abstain"
    reject = not match or la >= thresholds["synthetic"] or pa >= thresholds["replay"]
    return "reject" if reject else "accept"


def category(row):
    categories = []
    if row["origin"] == "human" and row["presentation"] == "direct":
        categories.append("target_reject" if row["relationship"] == "target"
                          else "impostor_accept")
    if row["origin"] == "synthetic":
        categories.append("synthetic_accept")
    if row["presentation"] == "replay":
        categories.append("replay_accept")
    return categories


def sample_rates(rows, thresholds, *, speaker_only=False):
    outcomes = defaultdict(list)
    for row in rows:
        d = decision(row, thresholds, speaker_only=speaker_only)
        group = category(row)
        for key in group:
            if speaker_only and key not in ("target_reject", "impostor_accept"):
                continue
            if key == "target_reject":
                error = d == "reject"
            else:
                error = d == "accept"
            outcomes[key].append((row["actual_speaker"], row["probe_session"], error, d == "abstain"))
            outcomes["abstention:" + key].append((row["actual_speaker"], row["probe_session"], d == "abstain", d == "abstain"))
    return outcomes


def error_rate(outcomes, key):
    samples = outcomes.get(key, [])
    return sum(r[2] for r in samples) / len(samples) if samples else None


def optimize_calibration(rows, *, speaker_only=False):
    """Search a small deterministic calibration-only grid, never assessment."""
    full = [row for row in rows if all(
        score_value(row, key) is not None for key in
        (["speaker_similarity"] if speaker_only else
         ["speaker_similarity", "synthetic_score", "replay_score"])
    )]
    def grid(name, default):
        values = sorted({score_value(r, name) for r in full})
        if not values:
            return [default]
        picks = {default}
        for idx in range(0, 11):
            position = int(idx * (len(values)-1) / 10)
            picks.add(values[position])
        return sorted(picks)
    speaker = grid("speaker_similarity", SPEAKER_BASELINE)
    la = ([LA_BASELINE] if speaker_only else grid("synthetic_score", LA_BASELINE))
    pa = ([PA_BASELINE] if speaker_only else grid("replay_score", PA_BASELINE))
    best = None
    count = 0
    for a in speaker:
        for b in la:
            for c in pa:
                thresholds = {"speaker": a, "synthetic": b, "replay": c}
                measures = sample_rates(rows, thresholds, speaker_only=speaker_only)
                relevant = ["target_reject", "impostor_accept"] if speaker_only else list(LIMITS)
                # Cannot fit a policy without all required supervised categories.
                if any(not measures.get(key if key != "abstention" else "abstention:target_reject")
                       for key in relevant):
                    continue
                rates = {key: error_rate(measures, key) for key in relevant
                         if key != "abstention"}
                if not speaker_only:
                    rates["abstention"] = max(error_rate(measures, "abstention:"+g)
                                            for g in ("target_reject", "impostor_accept",
                                                      "synthetic_accept", "replay_accept"))
                violation = sum(max(0, rates[k]-LIMITS[k]) / LIMITS[k]
                                for k in rates)
                count += 1
                objective = (violation, sum(rates.values()), a, b, c)
                if best is None or objective < best[0]:
                    best = (objective, thresholds, rates)
    if best is None:
        raise ValueError("Insufficient labeled calibration categories")
    return {"thresholds": best[1], "calibration_rates": best[2],
            "candidate_count": count,
            "calibration_constraints_met": best[0][0] == 0}


def one_sided_cluster_bound(samples):
    """Conservative one-sided 95% bound on error-affected independent clusters.

    Count a speaker as affected if any of its paired session trials errs.
    This avoids independent-trial assumptions; may be conservative.
    """
    from scipy.stats import beta
    clusters = defaultdict(list)
    for speaker, session, error, _ in samples:
        clusters[speaker].append(bool(error))
    n = len(clusters)
    errors = sum(any(x) for x in clusters.values())
    if n == 0:
        return None
    upper = 1.0 if errors == n else float(beta.ppf(.95, errors+1, n-errors))
    return {"independent_speakers": n, "affected_speakers": errors,
            "upper95_conservative": upper}


def validate_holdout(rows, thresholds, *, speaker_only=False):
    outcomes = sample_rates(rows, thresholds, speaker_only=speaker_only)
    groups = ["target_reject", "impostor_accept"] if speaker_only else [
        "target_reject", "impostor_accept", "synthetic_accept", "replay_accept"
    ]
    stats = {}
    passed = True
    for group in groups:
        samples = outcomes.get(group, [])
        upper = one_sided_cluster_bound(samples)
        abstentions = outcomes.get("abstention:" + group, [])
        abstain_bound = one_sided_cluster_bound(abstentions)
        n = len(samples)
        enough = upper is not None and upper["independent_speakers"] >= 10
        gpass = (enough and upper["upper95_conservative"] <= LIMITS[group]
                 and abstain_bound is not None
                 and abstain_bound["upper95_conservative"] <= LIMITS["abstention"])
        passed &= gpass
        stats[group] = {
            "trials": n, "error_trials": sum(r[2] for r in samples),
            "error_rate": error_rate(outcomes, group),
            "bound": upper, "abstention_bound": abstain_bound,
            "pass": bool(gpass),
        }
    return {"status": "pass" if passed else "not_passed",
            "per_class": stats}


def evaluate(rows):
    meta = verify_manifest(rows)
    calibration = [r for r in rows if r["partition"] == "calibration"]
    evaluation = [r for r in rows if r["partition"] == "assessment"]
    output = {"manifest": meta, "by_scope": {}, "thresholds_are_raw": True,
              "model_assets_must_be_verified_separately": True}
    for scope in meta["scopes"]:
        cal = [r for r in calibration if r["scope"] == scope]
        holdout = [r for r in evaluation if r["scope"] == scope]
        try:
            spk = optimize_calibration(cal, speaker_only=True)
            joint = optimize_calibration(cal, speaker_only=False)
            speaker_result = validate_holdout(holdout, spk["thresholds"], speaker_only=True)
            joint_result = validate_holdout(holdout, joint["thresholds"])
            if not spk["calibration_constraints_met"]:
                speaker_result["status"] = "not_passed"
            if not joint["calibration_constraints_met"]:
                joint_result["status"] = "not_passed"
            output["by_scope"][scope] = {
                "speaker_policy": spk, "joint_policy": joint,
                "gate8": speaker_result, "gate9": joint_result
            }
        except ValueError as err:
            output["by_scope"][scope] = {"gate8": {"status": "not_testable"},
                                         "gate9": {"status": "not_testable"},
                                         "reason": str(err)}
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    with args.manifest.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    blocked = False
    try:
        result = evaluate(rows)
    except ValueError as error:
        blocked = True
        result = {
            "gate8": {"status": "blocked"},
            "gate9": {"status": "blocked"},
            "reason": str(error),
            "assessment_performed": False,
            "never_promote_on_missing_labels": True,
        }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if blocked:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
