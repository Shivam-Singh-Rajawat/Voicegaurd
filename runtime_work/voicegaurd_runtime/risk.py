"""Interpretable prototype policy; not a calibrated attack probability."""
from dataclasses import dataclass
from math import isfinite
from collections import deque

@dataclass(frozen=True)
class Evidence:
    synthetic_score: float = None
    replay_score: float = None
    speaker_similarity: float = None
    quality_reliable: bool = True

def _unit(value,name):
    if value is None: return
    if not isfinite(value) or not 0<=value<=1: raise ValueError(name+" must be finite in [0,1]")

class RiskEngine:
    def __init__(self, synthetic_threshold, replay_threshold, speaker_threshold=None, window=5,
                 *, acquisition=None, expected_checkpoint=None):
        for name,value in [("synthetic_threshold",synthetic_threshold),("replay_threshold",replay_threshold)]:
            _unit(value,name)
            if value is None: raise ValueError("Spoof thresholds must be configured")
        if speaker_threshold is not None and (not isfinite(speaker_threshold) or not -1<=speaker_threshold<=1): raise ValueError("Invalid cosine threshold")
        if not isinstance(window,int) or window<1: raise ValueError("window must be a positive integer")
        self.thresholds=(synthetic_threshold,replay_threshold,speaker_threshold); self.history=deque(maxlen=window)
        self.acquisition = acquisition
        self.expected_checkpoint = expected_checkpoint

    def _abstain(self, reason):
        self.history.clear()
        return dict(level="uncertain", policy_score=None, reasons=[reason], calibrated=False)

    def update_from_inference(self, result, *, quality_reliable):
        """Apply the heuristic for a caller-verified acquisition scope."""
        if not quality_reliable:
            return self._abstain("Audio quality is unreliable")
        detector = {"la": "synthetic", "pa": "replay"}.get(self.acquisition)
        if detector is None or not self.expected_checkpoint:
            return self._abstain("Acquisition scope or checkpoint is unverified")
        evidence = result["evidence"].get(detector, {})
        score = evidence.get("score")
        if score is None or evidence.get("checkpoint") != self.expected_checkpoint:
            return self._abstain("Required detector score or checkpoint is unverified")

        similarity = None
        speaker_threshold = self.thresholds[2]
        if speaker_threshold is not None:
            speaker = result.get("speaker_verification")
            if (not isinstance(speaker, dict) or speaker.get("similarity") is None
                    or speaker.get("score_type") != "cosine_similarity"
                    or speaker.get("threshold") != speaker_threshold):
                return self._abstain("Required speaker score or cutoff is unverified")
            similarity = speaker["similarity"]

        scores = {detector + "_score": score}
        return self.update(Evidence(speaker_similarity=similarity, **scores))

    def update(self,evidence):
        _unit(evidence.synthetic_score,"synthetic_score"); _unit(evidence.replay_score,"replay_score")
        s=evidence.speaker_similarity
        if s is not None and (not isfinite(s) or not -1<=s<=1): raise ValueError("Invalid speaker similarity")
        if not evidence.quality_reliable:
            return self._abstain("Audio quality is unreliable")
        reasons=[]; hits=0; present=0
        for value,threshold,name in [(evidence.synthetic_score,self.thresholds[0],"synthetic"),(evidence.replay_score,self.thresholds[1],"replay")]:
            if value is not None:
                present+=1
                if value>threshold: hits+=1; reasons.append(name+" threshold exceeded")
        if s is not None and self.thresholds[2] is not None:
            present+=1
            if s<=self.thresholds[2]: hits+=1; reasons.append("Speaker mismatch")
        if not present:
            return self._abstain("No usable evidence")
        # Correlated detectors count as a single alert per chunk.
        self.history.append(bool(hits)); fraction=sum(self.history)/len(self.history)
        level="high" if len(self.history)>=3 and fraction>=.6 else "medium" if hits or fraction>0 else "low"
        return dict(level=level,policy_score=round(100*fraction,2),reasons=reasons or ["No current threshold exceeded"],calibrated=False,observed_chunks=len(self.history),missing_evidence=[name for value,name in [(evidence.synthetic_score,"synthetic"),(evidence.replay_score,"replay"),(s,"speaker")] if value is None])
