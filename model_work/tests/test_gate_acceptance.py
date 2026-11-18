import copy
import pytest

from model_work.gate_acceptance import (
    verify_manifest, optimize_calibration, evaluate, decision
)


def make_row(idx, partition, category):
    speaker = f"{partition}_{category}_person"
    relation = "impostor" if category == "impostor" else "target"
    origin = "synthetic" if category == "synthetic" else "human"
    presentation = "replay" if category == "replay" else "direct"
    score = {
        "target": (0.9, 0.001, 0.2),
        "impostor": (0.2, 0.001, 0.2),
        "synthetic": (0.9, 0.8, 0.3),
        "replay": (0.9, 0.001, 0.99),
    }[category]
    return {
        "trial_id": f"trial_{idx}",
        "scope": "file",
        "partition": partition,
        "probe_sha256": f"hash-probe-{idx}",
        "probe_session": f"session-probe-{idx}",
        "source_lineage": f"lineage-{idx}",
        "actual_speaker": speaker,
        "claimed_speaker": (f"{partition}_target_person"
                            if relation == "impostor" else speaker),
        "enrollment_sessions": f"session-enroll-{idx}",
        "enrollment_sha256s": f"hash-enroll-{idx}",
        "relationship": relation,
        "origin": origin,
        "presentation": presentation,
        "label_provenance": f"verified-labels-dataset-{idx}",
        "authorization_id": f"permission-{idx}",
        "speaker_similarity": str(score[0]),
        "synthetic_score": str(score[1]),
        "replay_score": str(score[2]),
    }


def rows():
    return [make_row(i, part, category)
            for i, (part, category) in enumerate(
                [(p, c) for p in ("calibration", "assessment")
                 for c in ("target", "impostor", "synthetic", "replay")], 1)]


def test_echo_fakelike_incomplete_metadata_cannot_pass():
    with pytest.raises(ValueError, match="Missing verified columns"):
        verify_manifest([{"trial_id": "EF_D_1", "label": "bonafide"}])


def test_enrollment_session_overlap_is_blocked():
    dataset = rows()
    dataset[0]["enrollment_sessions"] = dataset[0]["probe_session"]
    with pytest.raises(ValueError, match="Enrollment/probe session overlap"):
        verify_manifest(dataset)


def test_enrollment_audio_overlap_is_blocked():
    dataset = rows()
    dataset[0]["enrollment_sha256s"] = dataset[0]["probe_sha256"]
    with pytest.raises(ValueError, match="its own enrollment"):
        verify_manifest(dataset)


def test_same_speaker_appearing_across_partitions_blocked():
    dataset = rows()
    dataset[5]["actual_speaker"] = dataset[1]["actual_speaker"]
    with pytest.raises(ValueError, match="speaker overlap"):
        verify_manifest(dataset)


def test_source_lineage_overlap_blocked():
    dataset = rows()
    dataset[4]["source_lineage"] = dataset[0]["source_lineage"]
    with pytest.raises(ValueError, match="source lineage overlap"):
        verify_manifest(dataset)


def test_label_consistency_guard():
    dataset = rows()
    dataset[0]["relationship"] = "impostor"
    with pytest.raises(ValueError, match="contradicts"):
        verify_manifest(dataset)


def test_small_heldout_stays_unpassed_despite_perfect_point_scores():
    dataset = rows()
    result = evaluate(dataset)
    assert result["manifest"]["trials"] == 8
    assert result["by_scope"]["file"]["gate8"]["status"] == "not_passed"
    assert result["by_scope"]["file"]["gate9"]["status"] == "not_passed"
    assert result["by_scope"]["file"]["gate8"]["per_class"]["target_reject"]["trials"] == 1


def test_abstain_when_any_model_score_missing():
    row = make_row(1, "calibration", "target")
    thresholds = {"speaker": 0.4769, "synthetic": 0.006,
                  "replay": 0.936}
    assert decision(row, thresholds) == "accept"
    row["replay_score"] = ""
    assert decision(row, thresholds) == "abstain"
    assert decision(row, thresholds, speaker_only=True) == "accept"
    row["speaker_similarity"] = "unknown"
    assert decision(row, thresholds, speaker_only=True) == "abstain"
