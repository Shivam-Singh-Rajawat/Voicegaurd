import numpy as np
import pytest
from voicegaurd_runtime.streaming import AudioBuffer


def test_chunk_boundaries_preserve_overlapping_windows():
    b = AudioBuffer(window_seconds=2, hop_seconds=1)
    assert b.push(np.arange(15000)) == []
    windows = b.push(np.arange(15000, 50000))
    assert len(windows) == 2
    assert [w['start_seconds'] for w in windows] == [0, 1]
    assert np.array_equal(windows[0]['audio'], np.arange(32000))
    assert np.array_equal(windows[1]['audio'], np.arange(16000, 48000))
    assert len(b.pending) < b.window


def test_reset_clears_session():
    b = AudioBuffer()
    b.push(np.ones(100))
    b.reset()
    assert b.offset == 0 and len(b.pending) == 0


@pytest.mark.parametrize('samples', [[[1, 2]], [float('nan')], np.zeros(160001)])
def test_bad_chunks_rejected(samples):
    with pytest.raises(ValueError):
        AudioBuffer().push(samples)


def test_sessions_are_isolated():
    first, second = AudioBuffer(), AudioBuffer()
    first.push(np.ones(100))
    assert len(second.pending) == 0
