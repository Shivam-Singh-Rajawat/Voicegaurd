import numpy as np
import pytest

from voicegaurd_runtime.speaker import SpeakerVerifier


def test_enrollment_and_verification_preserve_frozen_decision_rule():
    def encode(audio):
        embedding = np.zeros(192, dtype=np.float32)
        embedding[0] = audio[0]
        return embedding

    verifier = SpeakerVerifier(encode, threshold=0.4769288897514343)
    template = verifier.enroll([np.ones(16000), np.full(16000, 2.0)])
    assert verifier.verify(np.ones(16000), template)["matched"]
    assert not verifier.verify(-np.ones(16000), template)["matched"]
    with pytest.raises(ValueError, match="silent"):
        verifier.verify(np.zeros(16000), template)
