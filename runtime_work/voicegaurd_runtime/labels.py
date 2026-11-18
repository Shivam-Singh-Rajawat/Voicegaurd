"""Mandatory explicit model prediction labels with scientific provenance.

These are *research* classifications at a frozen LA cutoff, not calibrated
probabilities or security decisions. Do not infer replay labels from PA on
arbitrary microphone or file recordings: domain shift is documented.
"""
import math

# Frozen standalone LA research threshold from the V1 launcher and model record.
LA_DIAGNOSTIC_CUTOFF = 0.0061066979542373995


def _speaker_label(result):
    speaker = result.get("speaker_verification")
    if isinstance(speaker, dict):
        matched = speaker.get("matched")
        if matched is True:
            return "Match (provisional)"
        if matched is False:
            return "Mismatch (provisional)"
    return "Unknown"


def prediction_label(result):
    """Return a visible categorical LA label even when evidence abstains.

    'Human' is the negative class of the frozen LA diagnostic classifier,
    not a guarantee the speaker is a human; label_validation is explicit.
    """
    evidence = result.get("evidence")
    synthetic = evidence.get("synthetic", {}) if isinstance(evidence, dict) else {}
    score = synthetic.get("score") if isinstance(synthetic, dict) else None
    if score is None:
        status = synthetic.get("status", "missing_evidence")
        return {
            "label": "Unknown",
            "speaker_prediction": _speaker_label(result),
            "reason": "The synthetic detector did not return a usable complete-window score.",
            "status": "abstained",
            "abstention_reason": status,
            "label_validation": "not_validated_for_this_input",
            "security_decision": "uncertain",
            "research_cutoff": LA_DIAGNOSTIC_CUTOFF,
            "calibrated": False,
        }
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise ValueError("Synthetic evidence must be a finite numeric score")
    if not math.isfinite(score) or not 0 <= score <= 1:
        raise ValueError("Synthetic evidence outside [0,1]")
    is_ai = score >= LA_DIAGNOSTIC_CUTOFF
    validation_warning = (
        "A small 2026-11-18 EchoFake development audit missed all 19 scored "
        "synthetic samples at this cutoff (nonrandom sample, not an "
        "independent benchmark). The Human label is therefore unreliable "
        "outside the original validated protocol."
    )
    return {
        "label": "AI-generated" if is_ai else "Human",
        "speaker_prediction": _speaker_label(result),
        "reason": (
            "The frozen LA diagnostic score exceeds its research cutoff. "
            "Acquisition-specific false positives remain possible."
            if is_ai else
            "The frozen LA diagnostic score is below its research cutoff. "
            "Many synthetic clips were missed on an external dataset, "
            "so this does not establish genuine human speech."
        ),
        "status": "provisional",
        "validation_warning": validation_warning,
        "abstention_reason": None,
        "label_validation": "not_validated_for_this_input",
        "security_decision": "uncertain",
        "research_cutoff": LA_DIAGNOSTIC_CUTOFF,
        "calibrated": False,
    }
