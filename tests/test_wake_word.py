"""
Tests for WakeWordListener. No real mic or model needed — the openWakeWord
model and PyAudio stream are faked, so we exercise the detection loop,
threshold/cooldown, pause/resume handoff, and graceful-disable logic.
"""
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from wake_word import WakeWordListener, FRAME_SAMPLES


class FakeModel:
    def __init__(self, score):
        self._score = score

    def predict(self, frame):
        return {"hey_jarvis": self._score}


class FakeStream:
    def read(self, n, exception_on_overflow=False):
        return b"\x00" * (FRAME_SAMPLES * 2)  # int16 silence, right length


def _wire_fake(listener, score):
    """Make start() use a fake model + stream instead of real hardware."""
    def fake_load():
        listener._model = FakeModel(score)
        listener.available = True
        return True
    listener._load_model = fake_load
    listener._open_stream = lambda: setattr(listener, "_stream", FakeStream())


class TestDetection:
    def test_fires_callback_above_threshold(self):
        hits = []
        lis = WakeWordListener(on_detect=lambda m, s: hits.append((m, s)), threshold=0.5)
        _wire_fake(lis, score=0.9)
        lis.start()
        time.sleep(0.25)
        lis.stop()
        assert hits, "callback should have fired for a high score"
        assert hits[0][0] == "hey_jarvis"

    def test_no_fire_below_threshold(self):
        hits = []
        lis = WakeWordListener(on_detect=lambda m, s: hits.append((m, s)), threshold=0.5)
        _wire_fake(lis, score=0.1)
        lis.start()
        time.sleep(0.2)
        lis.stop()
        assert not hits, "callback must not fire below threshold"

    def test_cooldown_debounces_repeats(self):
        hits = []
        lis = WakeWordListener(on_detect=lambda m, s: hits.append(s), threshold=0.5)
        _wire_fake(lis, score=0.99)
        lis.start()
        time.sleep(0.3)  # many frames, but all within the 3s cooldown
        lis.stop()
        assert len(hits) == 1, f"cooldown should collapse repeats to one, got {len(hits)}"


class TestPauseResume:
    def test_pause_resume_flags(self):
        lis = WakeWordListener(on_detect=lambda m, s: None)
        _wire_fake(lis, score=0.0)
        lis.start()
        lis.pause()
        assert lis._paused.is_set()
        lis.resume()
        assert not lis._paused.is_set()
        lis.stop()

    def test_resume_noop_when_unavailable(self):
        lis = WakeWordListener(on_detect=lambda m, s: None)
        lis.available = False
        lis._paused.set()
        lis.resume()  # should stay paused since it's not available
        assert lis._paused.is_set()


class TestGracefulDisable:
    def test_start_does_nothing_when_model_unavailable(self):
        lis = WakeWordListener(on_detect=lambda m, s: None)
        lis._load_model = lambda: False  # simulate openWakeWord/model missing
        lis.start()
        assert lis.available is False
        assert lis._thread is None

    def test_stop_safe_when_never_started(self):
        lis = WakeWordListener(on_detect=lambda m, s: None)
        lis.stop()  # must not raise
