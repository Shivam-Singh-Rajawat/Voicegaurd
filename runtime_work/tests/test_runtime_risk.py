import pytest
from voicegaurd_runtime.risk import Evidence,RiskEngine

def test_quality_and_missing_are_uncertainty():
 e=RiskEngine(.8,.9)
 assert e.update(Evidence())['level']=='uncertain'
 assert e.update(Evidence(.99,.99,quality_reliable=False))['level']=='uncertain'
 assert len(e.history)==0

def test_temporal_alert_and_recovery():
 e=RiskEngine(.8,.9,window=3)
 assert e.update(Evidence(.9,.95))['policy_score']==100
 assert e.update(Evidence(.9))['level']=='medium'
 assert e.update(Evidence(.9))['level']=='high'
 for _ in range(3): out=e.update(Evidence(.1,.1))
 assert out['level']=='low'

def test_invalid_scores_rejected():
 e=RiskEngine(.8,.9)
 for value in [float('nan'),float('inf'),-1,2]:
  with pytest.raises(ValueError): e.update(Evidence(value))

def test_speaker_requires_configured_threshold():
 assert RiskEngine(.8,.9).update(Evidence(speaker_similarity=.1))['level']=='uncertain'
 e=RiskEngine(.8,.9,speaker_threshold=.5)
 assert 'Speaker mismatch' in e.update(Evidence(speaker_similarity=.1))['reasons']


@pytest.mark.parametrize("gap", [Evidence(), Evidence(quality_reliable=False)])
def test_evidence_gap_ends_consecutive_alert_run(gap):
    engine = RiskEngine(0.8, 0.9, window=5)
    for _ in range(4):
        assert engine.update(Evidence(synthetic_score=0.95))["level"] in {"medium", "high"}
    assert engine.update(gap)["level"] == "uncertain"
    resumed = engine.update(Evidence(synthetic_score=0.1))
    assert resumed["level"] == "low"
    assert resumed["observed_chunks"] == 1


def test_speaker_cutoff_matches_strict_verifier_acceptance():
    engine = RiskEngine(0.8, 0.9, speaker_threshold=0.5)
    assert "Speaker mismatch" in engine.update(Evidence(speaker_similarity=0.5))["reasons"]


def test_scoped_inference_requires_matching_evidence_and_ignores_other_domain():
    engine = RiskEngine(.8, .9, speaker_threshold=.5, acquisition="la", expected_checkpoint="la.pt")
    result = {"evidence": {"synthetic": {"score": .1, "checkpoint": "la.pt"},
                           "replay": {"score": .99, "checkpoint": "pa.pt"}},
              "speaker_verification": {"similarity": .8, "threshold": .5,
                                       "score_type": "cosine_similarity"}}
    assert engine.update_from_inference(result, quality_reliable=True)["level"] == "low"
    assert engine.update_from_inference(result, quality_reliable=False)["level"] == "uncertain"
    assert RiskEngine(.8, .9).update_from_inference(result, quality_reliable=True)["level"] == "uncertain"
    result["speaker_verification"]["threshold"] = .6
    assert engine.update_from_inference(result, quality_reliable=True)["level"] == "uncertain"
    result["speaker_verification"]["threshold"] = .5
    result["evidence"]["synthetic"]["checkpoint"] = "unexpected.pt"
    assert engine.update_from_inference(result, quality_reliable=True)["level"] == "uncertain"
