import math
import pytest

from voicegaurd_runtime.labels import LA_DIAGNOSTIC_CUTOFF, prediction_label


def test_prediction_abstains_for_unavailable_or_short_input():
    for result in (
        {},
        {"evidence": {"synthetic": {"score": None, "status": "insufficient_audio"}}},
        {"evidence": {"synthetic": {"score": None, "status": "no_signal"}}},
    ):
        got = prediction_label(result)
        assert got["label"] == "Unknown"
        assert got["status"] == "abstained"
        assert got["security_decision"] == "uncertain"
        assert got["calibrated"] is False


def test_label_is_explicit_provisional_not_security_validation():
    ai = prediction_label({"evidence": {"synthetic": {"score": LA_DIAGNOSTIC_CUTOFF}}})
    human = prediction_label({"evidence": {"synthetic": {"score": 0.0001}}})
    assert ai["label"] == "AI-generated"
    assert human["label"] == "Human"
    for row in (ai, human):
        assert row["status"] == "provisional"
        assert row["label_validation"] == "not_validated_for_this_input"
        assert row["security_decision"] == "uncertain"
        assert row["calibrated"] is False
    assert "Many synthetic clips were missed" in human["reason"]


@pytest.mark.parametrize("score", [-0.1, 1.1, float("nan"), float("inf"), True, "fake"])
def test_malformed_synthetic_evidence_rejected(score):
    with pytest.raises(ValueError):
        prediction_label({"evidence": {"synthetic": {"score": score}}})


def test_speaker_prediction_is_research_only_and_can_be_missing():
    evidence = {"evidence": {"synthetic": {"score": 0.02}}}
    assert prediction_label(evidence)["speaker_prediction"] == "Unknown"
    evidence["speaker_verification"] = {"matched": True, "similarity": 0.8}
    matched = prediction_label(evidence)
    assert matched["speaker_prediction"] == "Match (provisional)"
    assert matched["security_decision"] == "uncertain"
    evidence["speaker_verification"] = {"matched": False, "similarity": 0.2}
    assert prediction_label(evidence)["speaker_prediction"] == "Mismatch (provisional)"
